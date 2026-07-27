package main

import (
	"testing"

	"github.com/hashicorp/terraform-plugin-sdk/v2/helper/schema"
)

func TestProviderAcknowledgementContractRequiresImmutableBindings(t *testing.T) {
	p := provider()
	if err := p.InternalValidate(); err != nil {
		t.Fatalf("provider schema is invalid: %v", err)
	}
	resource := p.ResourcesMap["cell_config_acknowledgement"]
	for _, name := range []string{
		"contract_checksum",
		"schedule_group_arn",
		"scheduler_delivery_role_arn",
		"scheduler_delivery_role_id",
		"launch_role_arn",
		"launch_role_id",
		"task_family",
		"task_definition_arn",
		"repository_id",
		"terraform_root_id",
	} {
		field, ok := resource.Schema[name]
		if !ok || !field.Required || !field.ForceNew {
			t.Fatalf("%s must be a required immutable acknowledgement binding", name)
		}
	}
}

func TestProviderSupportsMaterializedActivationAcknowledgements(t *testing.T) {
	resource := provider().ResourcesMap["cell_config_acknowledgement"]
	field, ok := resource.Schema["required_lifecycle"]
	if !ok || !field.Optional || !field.ForceNew || field.Default != "VALIDATED" {
		t.Fatal("required_lifecycle must default to VALIDATED and be immutable")
	}
	if _, ok := resource.Schema["conformance_result"]; !ok {
		t.Fatal("conformance_result must be exposed from the authoritative acknowledgement")
	}
}

func TestAcknowledgementRejectsWrongEndpointBeforeAuthentication(t *testing.T) {
	p := provider()
	data := schema.TestResourceDataRaw(t, p.ResourcesMap["cell_config_acknowledgement"].Schema, map[string]interface{}{
		"account_id":                  "111111111111",
		"environment":                 "dev",
		"job_id":                      "dev/sample/daily",
		"config_version":              "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
		"contract_endpoint_url":       "https://validator.example/validate",
		"contract_version":            "1.0.0",
		"contract_checksum":           "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
		"publisher_role_arn":          "arn:aws:iam::111111111111:role/validator",
		"ownership_generation":        1,
		"schedule_generation":         "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
		"schedule_arn":                "arn:aws:scheduler:us-east-1:111111111111:schedule/cell/daily",
		"schedule_group_arn":          "arn:aws:scheduler:us-east-1:111111111111:schedule-group/cell",
		"scheduler_delivery_role_arn": "arn:aws:iam::111111111111:role/scheduler",
		"scheduler_delivery_role_id":  "AROASCHEDULER",
		"launch_role_arn":             "arn:aws:iam::111111111111:role/launch",
		"launch_role_id":              "AROALAUNCH",
		"task_family":                 "daily",
		"task_definition_arn":         "arn:aws:ecs:us-east-1:111111111111:task-definition/daily:1",
		"repository_id":               "repo",
		"terraform_root_id":           "root",
	})
	err := acknowledge(data, &clientConfig{endpoint: "https://different.example/validate", region: "us-east-1", roleARN: "arn:aws:iam::111111111111:role/validator"})
	if err == nil {
		t.Fatal("expected endpoint mismatch")
	}
}
