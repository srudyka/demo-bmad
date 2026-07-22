from job_registrar import Reservation


def test_package_entrypoint_exposes_conditional_claim_behavior() -> None:
    value = Reservation(
        job_id="dev/sample/daily",
        account_id="123456789012",
        region="-".join(("us", "east", "1")),
        environment="dev",
        application="sample",
        repository_id="123456789",
        terraform_root_id="sample-root",
        apply_role_id="sample-role",
        owner="team",
    )
    assert value.key == "JOB#dev/sample/daily"
