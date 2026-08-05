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
				Read: func(data *schema.ResourceData, _ interface{}) error {
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
			"cell_config_acknowledgement": {
				Create: acknowledge,
				Read: func(data *schema.ResourceData, _ interface{}) error {
					// The endpoint has no safe remote read operation. Clear the ID so
					// Terraform fails closed and recreates the immutable acknowledgement.
					// Never retain a stale VALIDATED result in state.
					data.SetId("")
					return nil
				},
				Delete: func(*schema.ResourceData, interface{}) error { return nil },
				Schema: map[string]*schema.Schema{
					"account_id":                  {Type: schema.TypeString, Required: true, ForceNew: true},
					"environment":                 {Type: schema.TypeString, Required: true, ForceNew: true},
					"job_id":                      {Type: schema.TypeString, Required: true, ForceNew: true},
					"config_version":              {Type: schema.TypeString, Required: true, ForceNew: true},
					"contract_endpoint_url":       {Type: schema.TypeString, Required: true, ForceNew: true},
					"contract_version":            {Type: schema.TypeString, Required: true, ForceNew: true},
					"contract_checksum":           {Type: schema.TypeString, Required: true, ForceNew: true},
					"publisher_role_arn":          {Type: schema.TypeString, Required: true, ForceNew: true},
					"ownership_generation":        {Type: schema.TypeInt, Required: true, ForceNew: true},
					"schedule_generation":         {Type: schema.TypeString, Required: true, ForceNew: true},
					"schedule_arn":                {Type: schema.TypeString, Required: true, ForceNew: true},
					"schedule_group_arn":          {Type: schema.TypeString, Required: true, ForceNew: true},
					"scheduler_delivery_role_arn": {Type: schema.TypeString, Required: true, ForceNew: true},
					"scheduler_delivery_role_id":  {Type: schema.TypeString, Required: true, ForceNew: true},
					"launch_role_arn":             {Type: schema.TypeString, Required: true, ForceNew: true},
					"launch_role_id":              {Type: schema.TypeString, Required: true, ForceNew: true},
					"task_family":                 {Type: schema.TypeString, Required: true, ForceNew: true},
					"task_definition_arn":         {Type: schema.TypeString, Required: true, ForceNew: true},
					"repository_id":               {Type: schema.TypeString, Required: true, ForceNew: true},
					"terraform_root_id":           {Type: schema.TypeString, Required: true, ForceNew: true},
					"required_lifecycle":          {Type: schema.TypeString, Optional: true, Default: "VALIDATED", ForceNew: true},
					"result":                      {Type: schema.TypeString, Computed: true},
					"validated_at":                {Type: schema.TypeString, Computed: true},
					"horizon_watermark":           {Type: schema.TypeString, Computed: true},
					"validation_evidence":         {Type: schema.TypeString, Computed: true},
					"conformance_result":          {Type: schema.TypeString, Computed: true},
				},
			},
		},
	}
}

func acknowledge(data *schema.ResourceData, raw interface{}) error {
	ctx := context.Background()
	config := raw.(*clientConfig)
	if data.Get("contract_endpoint_url").(string) != config.endpoint {
		return fmt.Errorf("Cell acknowledgement endpoint does not match the configured provider endpoint")
	}
	if data.Get("publisher_role_arn").(string) != config.roleARN || config.roleARN == "" {
		return fmt.Errorf("Cell validator role does not match the declared provider role")
	}
	registration := map[string]interface{}{
		"account_id":                  data.Get("account_id"),
		"config_version":              data.Get("config_version"),
		"environment":                 data.Get("environment"),
		"job_id":                      data.Get("job_id"),
		"owner_generation":            data.Get("ownership_generation"),
		"region":                      config.region,
		"schedule_arn":                data.Get("schedule_arn"),
		"schedule_generation":         data.Get("schedule_generation"),
		"schedule_group_arn":          data.Get("schedule_group_arn"),
		"scheduler_delivery_role_arn": data.Get("scheduler_delivery_role_arn"),
		"scheduler_delivery_role_id":  data.Get("scheduler_delivery_role_id"),
		"launch_role_arn":             data.Get("launch_role_arn"),
		"launch_role_id":              data.Get("launch_role_id"),
		"task_family":                 data.Get("task_family"),
		"task_definition_arn":         data.Get("task_definition_arn"),
		"repository_id":               data.Get("repository_id"),
		"terraform_root_id":           data.Get("terraform_root_id"),
		"contract_version":            data.Get("contract_version"),
		"contract_checksum":           data.Get("contract_checksum"),
		"required_lifecycle":          data.Get("required_lifecycle"),
	}
	body, err := json.Marshal(map[string]interface{}{"registration": registration})
	if err != nil {
		return fmt.Errorf("encode acknowledgement request: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, config.endpoint, strings.NewReader(string(body)))
	if err != nil {
		return fmt.Errorf("build acknowledgement request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if err := sign(ctx, req, body, config.region, config.roleARN); err != nil {
		return err
	}
	resp, err := (&http.Client{Timeout: 30 * time.Second}).Do(req)
	if err != nil {
		return fmt.Errorf("invoke Cell validator: %w", err)
	}
	defer resp.Body.Close()
	responseBody, err := io.ReadAll(io.LimitReader(resp.Body, 64*1024))
	if err != nil {
		return fmt.Errorf("read Cell validator response: %w", err)
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("Cell validator rejected request: status=%d", resp.StatusCode)
	}
	var envelope struct {
		StatusCode int             `json:"statusCode"`
		Body       json.RawMessage `json:"body"`
	}
	if err := json.Unmarshal(responseBody, &envelope); err != nil {
		return fmt.Errorf("decode Cell validator response: %w", err)
	}
	if envelope.StatusCode != 0 && (envelope.StatusCode < 200 || envelope.StatusCode >= 300) {
		return fmt.Errorf("Cell validator returned status=%d", envelope.StatusCode)
	}
	acknowledgement := envelope.Body
	if len(acknowledgement) > 0 && acknowledgement[0] == '"' {
		var encoded string
		if err := json.Unmarshal(acknowledgement, &encoded); err != nil {
			return fmt.Errorf("decode Cell validator body: %w", err)
		}
		acknowledgement = json.RawMessage(encoded)
	}
	if len(acknowledgement) == 0 {
		acknowledgement = responseBody
	}
	var result struct {
		Validated          bool   `json:"validated"`
		Lifecycle          string `json:"lifecycle"`
		JobID              string `json:"job_id"`
		Config             string `json:"config_version"`
		Generation         int    `json:"ownership_generation"`
		Account            string `json:"account_id"`
		Environment        string `json:"environment"`
		ValidatedAt        string `json:"validated_at"`
		Contract           string `json:"contract_version"`
		ContractHash       string `json:"contract_checksum"`
		Schedule           string `json:"schedule_arn"`
		ScheduleGroup      string `json:"schedule_group_arn"`
		SchedulerRole      string `json:"scheduler_delivery_role_arn"`
		RoleID             string `json:"scheduler_delivery_role_id"`
		LaunchRole         string `json:"launch_role_arn"`
		LaunchRoleID       string `json:"launch_role_id"`
		TaskFamily         string `json:"task_family"`
		TaskDefinition     string `json:"task_definition_arn"`
		ScheduleGeneration string `json:"schedule_generation"`
		Repository         string `json:"repository_id"`
		TerraformRoot      string `json:"terraform_root_id"`
		Conformance        string `json:"conformance_result"`
		Watermark          string `json:"horizon_watermark"`
		Evidence           string `json:"validation_evidence"`
	}
	if err := json.Unmarshal(acknowledgement, &result); err != nil {
		return fmt.Errorf("decode Cell acknowledgement: %w", err)
	}
	if !result.Validated || result.Lifecycle != data.Get("required_lifecycle") || result.JobID != data.Get("job_id") ||
		result.Config != data.Get("config_version") || result.Generation != data.Get("ownership_generation") ||
		result.Account != data.Get("account_id") || result.Environment != data.Get("environment") ||
		result.Contract != data.Get("contract_version") || result.ContractHash != data.Get("contract_checksum") ||
		result.Schedule != data.Get("schedule_arn") || result.ScheduleGroup != data.Get("schedule_group_arn") ||
		result.ScheduleGeneration != data.Get("schedule_generation") ||
		result.SchedulerRole != data.Get("scheduler_delivery_role_arn") ||
		result.RoleID != data.Get("scheduler_delivery_role_id") || result.LaunchRole != data.Get("launch_role_arn") ||
		result.LaunchRoleID != data.Get("launch_role_id") || result.TaskFamily != data.Get("task_family") ||
		result.TaskDefinition != data.Get("task_definition_arn") ||
		result.Repository != data.Get("repository_id") || result.TerraformRoot != data.Get("terraform_root_id") ||
		result.Watermark == "" || result.Evidence == "" {
		return fmt.Errorf("Cell validator returned an invalid acknowledgement contract")
	}
	data.SetId(fmt.Sprintf("%s/%s", data.Get("job_id"), data.Get("config_version")))
	if err := data.Set("result", result.Lifecycle); err != nil {
		return err
	}
	if err := data.Set("validated_at", result.ValidatedAt); err != nil {
		return err
	}
	if err := data.Set("horizon_watermark", result.Watermark); err != nil {
		return err
	}
	if err := data.Set("validation_evidence", result.Evidence); err != nil {
		return err
	}
	return data.Set("conformance_result", result.Conformance)
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
