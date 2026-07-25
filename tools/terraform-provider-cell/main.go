package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/aws/signer/v4"
	awscfg "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials/stscreds"
	"github.com/aws/aws-sdk-go-v2/service/sts"
	"github.com/hashicorp/terraform-plugin-sdk/v2/diag"
	"github.com/hashicorp/terraform-plugin-sdk/v2/helper/schema"
	"github.com/hashicorp/terraform-plugin-sdk/v2/plugin"
)

const protocolVersion = "config-publisher/1.0.0"

type clientConfig struct {
	endpoint string
	region   string
	roleARN  string
}

func provider() *schema.Provider {
	return &schema.Provider{
		ConfigureContextFunc: func(_ context.Context, data *schema.ResourceData) (interface{}, diag.Diagnostics) {
			return &clientConfig{endpoint: data.Get("endpoint_url").(string), region: data.Get("region").(string), roleARN: data.Get("publisher_role_arn").(string)}, nil
		},
		Schema: map[string]*schema.Schema{
			"endpoint_url":       {Type: schema.TypeString, Required: true, ForceNew: true},
			"region":             {Type: schema.TypeString, Optional: true, DefaultFunc: schema.EnvDefaultFunc("AWS_REGION", "")},
			"publisher_role_arn": {Type: schema.TypeString, Required: true, ForceNew: true},
		},
		ResourcesMap: map[string]*schema.Resource{
			"cell_config_publication": {
				Create: publish,
				Read: func(_ *schema.ResourceData, _ interface{}) error {
					return fmt.Errorf("Cell publisher does not support remote refresh; recreate the publication if the CONFIG object is missing")
				},
				Delete: func(*schema.ResourceData, interface{}) error { return nil },
				Schema: map[string]*schema.Schema{
					"job_id":                {Type: schema.TypeString, Required: true, ForceNew: true},
					"config_version":        {Type: schema.TypeString, Required: true, ForceNew: true},
					"object_key":            {Type: schema.TypeString, Required: true, ForceNew: true},
					"contract_endpoint_url": {Type: schema.TypeString, Required: true, ForceNew: true},
					"config_document":       {Type: schema.TypeString, Required: true, ForceNew: true, Sensitive: true},
					"contract_version":      {Type: schema.TypeString, Required: true, ForceNew: true},
					"ownership_generation":  {Type: schema.TypeInt, Required: true, ForceNew: true},
					"publisher_role_arn":    {Type: schema.TypeString, Required: true, ForceNew: true},
					"result":                {Type: schema.TypeString, Computed: true},
				},
			},
		},
	}
}

func publish(data *schema.ResourceData, raw interface{}) error {
	ctx := context.Background()
	config := raw.(*clientConfig)
	if data.Get("contract_endpoint_url").(string) != config.endpoint {
		return fmt.Errorf("Cell publisher endpoint does not match the discovered contract")
	}
	if data.Get("publisher_role_arn").(string) != config.roleARN || config.roleARN == "" {
		return fmt.Errorf("Cell publisher role does not match the declared provider role")
	}
	document := json.RawMessage(data.Get("config_document").(string))
	payload := map[string]interface{}{
		"protocol_version":     protocolVersion,
		"job_id":               data.Get("job_id"),
		"config_version":       data.Get("config_version"),
		"object_key":           data.Get("object_key"),
		"config_document":      json.RawMessage(document),
		"contract_version":     data.Get("contract_version"),
		"ownership_generation": data.Get("ownership_generation"),
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("encode publisher request: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, config.endpoint, strings.NewReader(string(body)))
	if err != nil {
		return fmt.Errorf("build publisher request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if err := sign(ctx, req, body, config.region, config.roleARN); err != nil {
		return err
	}
	resp, err := (&http.Client{Timeout: 30 * time.Second}).Do(req)
	if err != nil {
		return fmt.Errorf("invoke Cell publisher: %w", err)
	}
	defer resp.Body.Close()
	responseBody, err := io.ReadAll(io.LimitReader(resp.Body, 64*1024))
	if err != nil {
		return fmt.Errorf("read Cell publisher response: %w", err)
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("Cell publisher rejected request: status=%d", resp.StatusCode)
	}
	var result struct {
		ProtocolVersion     string `json:"protocol_version"`
		Lifecycle           string `json:"lifecycle"`
		Result              string `json:"result"`
		JobID               string `json:"job_id"`
		ConfigVersion       string `json:"config_version"`
		ObjectKey           string `json:"object_key"`
		ContractVersion     string `json:"contract_version"`
		OwnershipGeneration int    `json:"ownership_generation"`
		OperationID         string `json:"operation_id"`
	}
	if err := json.Unmarshal(responseBody, &result); err != nil {
		return fmt.Errorf("decode Cell publisher response: %w", err)
	}
	if result.ProtocolVersion != protocolVersion || result.Lifecycle != "PUBLISHED" ||
		(result.Result != "PUBLISHED" && result.Result != "ALREADY_PUBLISHED") ||
		result.JobID != data.Get("job_id") || result.ConfigVersion != data.Get("config_version") ||
		result.ObjectKey != data.Get("object_key") || result.ContractVersion != data.Get("contract_version") ||
		result.OwnershipGeneration != data.Get("ownership_generation") || !strings.HasPrefix(result.OperationID, "cfgpub-") {
		return fmt.Errorf("Cell publisher returned an invalid response contract")
	}
	data.SetId(fmt.Sprintf("%s/%s", data.Get("job_id"), data.Get("config_version")))
	if err := data.Set("result", result.Result); err != nil {
		return err
	}
	return nil
}

func sign(ctx context.Context, req *http.Request, body []byte, region string, roleARN string) error {
	if region == "" {
		return fmt.Errorf("AWS_REGION is required for Cell publisher authentication")
	}
	cfg, err := awscfg.LoadDefaultConfig(ctx, awscfg.WithRegion(region))
	if err != nil {
		return fmt.Errorf("load AWS credentials: %w", err)
	}
	hash := sha256.Sum256(body)
	var credentials aws.Credentials
	if roleARN != "" {
		provider := stscreds.NewAssumeRoleProvider(sts.NewFromConfig(cfg), roleARN)
		credentials, err = provider.Retrieve(ctx)
	} else {
		credentials, err = cfg.Credentials.Retrieve(ctx)
	}
	if err != nil {
		return fmt.Errorf("retrieve publisher role credentials: %w", err)
	}
	return v4.NewSigner().SignHTTP(ctx, credentials, req, hex.EncodeToString(hash[:]), "execute-api", region, time.Now())
}

func main() {
	plugin.Serve(&plugin.ServeOpts{ProviderFunc: func() *schema.Provider { return provider() }})
}
