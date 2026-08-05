resource "aws_security_group" "job" {
  count = var.networking.security_group_mode == "create" ? 1 : 0

  name                   = "${local.name_prefix}-task"
  description            = "Bounded egress security group for ${local.job_id}"
  vpc_id                 = var.networking.vpc_id
  revoke_rules_on_delete = true
  ingress                = []
  egress                 = []
  tags                   = local.merged_tags

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_vpc_security_group_egress_rule" "job" {
  for_each = var.networking.security_group_mode == "create" ? var.networking.egress_rules : {}

  security_group_id            = aws_security_group.job[0].id
  ip_protocol                  = each.value.protocol
  from_port                    = each.value.from_port
  to_port                      = each.value.to_port
  cidr_ipv4                    = try(each.value.cidr_ipv4, null)
  cidr_ipv6                    = try(each.value.cidr_ipv6, null)
  prefix_list_id               = try(each.value.prefix_list_id, null)
  referenced_security_group_id = try(each.value.referenced_security_group_id, null)
  description                  = "Approved bounded egress for ${local.job_id}: ${each.key}"

}
