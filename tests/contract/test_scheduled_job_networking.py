import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "modules" / "ecs-scheduled-job"
CATALOG = ROOT / "contracts" / "v1" / "catalogs" / "network.json"
FIXTURE = ROOT / "contracts" / "v1" / "fixtures" / "network" / "cases.json"


def test_network_catalog_is_versioned_and_fails_closed_by_contract() -> None:
    catalog = json.loads(CATALOG.read_text())
    assert catalog["schema_version"] == "1.0.0"
    assert catalog["policy_version"] == "1.0.0"
    assert catalog["unknown_policy_disposition"] == "BLOCK"
    assert catalog["exception_policy"]["owner"]
    assert (
        catalog["exception_policy"]["enforcement_stage"]
        in catalog["enforcement_stages"]
    )
    assert all(
        severity == "blocking" for severity in catalog["finding_severity"].values()
    )
    assert catalog["private_subnet_evidence"]["required"]
    assert set(catalog["security_group"]["allowed_egress_sources"]) == {
        "security-group",
        "prefix-list",
        "bounded-cidr",
    }
    assert set(catalog["dependency_paths"]) == {
        "nat",
        "vpc-endpoint",
        "privatelink",
        "proxy",
        "stable-egress",
        "internal",
    }
    assert catalog["enforcement_stages"] == ["non-production", "production"]
    assert set(catalog["finding_codes"]) >= {
        "NETWORK_POLICY_UNKNOWN",
        "NETWORK_SUBNET_NOT_PRIVATE",
        "NETWORK_SECURITY_GROUP_PUBLIC_INGRESS",
        "NETWORK_EGRESS_UNRESTRICTED",
        "NETWORK_DEPENDENCY_REACHABILITY_MISSING",
    }


def test_network_interface_is_explicit_and_public_ip_is_not_consumer_configurable() -> (
    None
):
    variables = (MODULE / "variables.tf").read_text()
    outputs = (MODULE / "outputs.tf").read_text()
    assert 'security_group_mode = optional(string, "existing")' in variables
    assert "vpc_id" in variables
    assert "policy_version" in variables
    assert "dependency_reachability" in variables
    assert "security_group_owner_account_ids" in variables
    assert "route_table_id" in variables
    assert 'assign_public_ip          = "DISABLED"' in outputs
    assert 'output "networking"' in outputs
    assert (
        "assign_public_ip"
        not in variables.split('variable "networking"', 1)[1].split(
            'variable "notification"', 1
        )[0]
    )


def test_network_module_owns_only_optional_job_security_group() -> None:
    terraform = "\n".join(path.read_text() for path in MODULE.glob("*.tf"))
    assert 'resource "aws_security_group" "job"' in terraform
    assert terraform.count('resource "aws_security_group"') == 1
    validation = (ROOT / "scripts" / "validate.py").read_text()
    assert "CKV2_AWS_5" in validation
    assert "single optional job security group" in validation
    assert 'resource "aws_vpc_security_group_egress_rule" "job"' in terraform
    assert 'resource "aws_vpc_security_group_ingress_rule"' not in terraform
    for prohibited in (
        'resource "aws_route"',
        'resource "aws_route_table"',
        'resource "aws_nat_gateway"',
        'resource "aws_vpc_endpoint"',
        'resource "aws_subnet"',
    ):
        assert prohibited not in terraform


def test_network_validation_covers_private_evidence_and_dependency_paths() -> None:
    main = (MODULE / "main.tf").read_text()
    network = (MODULE / "network.tf").read_text()
    variables = (MODULE / "variables.tf").read_text()
    catalog = CATALOG.read_text()
    for finding in (
        "NETWORK_POLICY_UNKNOWN",
        "NETWORK_SUBNET_NOT_PRIVATE",
        "NETWORK_SUBNET_VPC_MISMATCH",
        "NETWORK_SECURITY_GROUP_PUBLIC_INGRESS",
        "NETWORK_EGRESS_UNRESTRICTED",
        "NETWORK_DEPENDENCY_REACHABILITY_MISSING",
        "NETWORK_SECRET_PATH_MISMATCH",
    ):
        assert finding in main or finding in network
    for path_kind in (
        "nat",
        "vpc-endpoint",
        "privatelink",
        "proxy",
        "stable-egress",
        "internal",
    ):
        assert path_kind in variables or path_kind in catalog


def test_basic_example_declares_private_network_policy_and_reachability() -> None:
    example = (MODULE / "examples" / "basic" / "main.tf").read_text()
    assert 'vpc_id              = "vpc-' in example
    assert 'security_group_mode = "existing"' in example
    assert 'policy_version      = "1.0.0"' in example
    assert "dependency_reachability" in example
    assert "assign_public_ip" not in example
    assert "route_table_id" in example


def test_network_fixture_suite_covers_positive_and_negative_enforcement_paths() -> None:
    fixture = json.loads(FIXTURE.read_text())
    assert fixture["schema_version"] == "1.0.0"
    assert len(fixture["cases"]) >= 8
    assert any(not case["expected_findings"] for case in fixture["cases"])
    assert any(case["expected_findings"] for case in fixture["cases"])

    for case in fixture["cases"]:
        inputs = case["input"]
        findings = []
        if inputs.get("duplicate_subnets"):
            findings.append("NETWORK_SUBNET_DUPLICATE")
        elif not inputs.get("subnets_private", True):
            findings.append("NETWORK_SUBNET_NOT_PRIVATE")
        if inputs.get("az_supported") is False:
            findings.append("NETWORK_SUBNET_AZ_UNSUPPORTED")
        if inputs.get("public_ingress"):
            findings.append("NETWORK_SECURITY_GROUP_PUBLIC_INGRESS")
        if inputs.get("unrestricted_egress"):
            findings.append("NETWORK_EGRESS_UNRESTRICTED")
        if not inputs.get("dependency_reachable", True):
            findings.append("NETWORK_DEPENDENCY_REACHABILITY_MISSING")
        if not inputs.get("policy_known", True):
            findings.append("NETWORK_POLICY_UNKNOWN")
        if not inputs.get("secret_path_matches", True):
            findings.append("NETWORK_SECRET_PATH_MISMATCH")
        assert findings == case["expected_findings"], case["name"]
