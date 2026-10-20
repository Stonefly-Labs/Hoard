locals {
  name = "hoard-${var.environment}"
  tags = {
    project     = "Hoard"
    environment = var.environment
    managed_by  = "OpenTofu"
    purpose     = "github-oidc-bootstrap"
  }
  oidc_subject = "repo:${var.github_owner}/${var.github_repository}:environment:${var.environment}"
  github_variables = {
    AZURE_CLIENT_ID       = azurerm_user_assigned_identity.deploy.client_id
    AZURE_TENANT_ID       = azurerm_user_assigned_identity.deploy.tenant_id
    AZURE_SUBSCRIPTION_ID = var.subscription_id
    AZURE_RESOURCE_GROUP  = azurerm_resource_group.deploy.name
    AZURE_LOCATION        = var.location
  }
}

resource "azurerm_resource_group" "deploy" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_user_assigned_identity" "deploy" {
  name                = "id-${local.name}-github"
  location            = azurerm_resource_group.deploy.location
  resource_group_name = azurerm_resource_group.deploy.name
  tags                = local.tags
}

resource "azurerm_federated_identity_credential" "github" {
  name                      = "github-${var.environment}"
  user_assigned_identity_id = azurerm_user_assigned_identity.deploy.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = local.oidc_subject
}

resource "azurerm_role_assignment" "deploy" {
  scope                            = azurerm_resource_group.deploy.id
  role_definition_name             = "Contributor"
  principal_id                     = azurerm_user_assigned_identity.deploy.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "github_repository_environment" "deploy" {
  repository  = var.github_repository
  environment = var.environment

  deployment_branch_policy {
    protected_branches     = false
    custom_branch_policies = true
  }
}

resource "github_repository_environment_deployment_policy" "main" {
  repository     = var.github_repository
  environment    = github_repository_environment.deploy.environment
  branch_pattern = "main"
}

resource "github_actions_environment_variable" "azure" {
  for_each = local.github_variables

  repository    = var.github_repository
  environment   = github_repository_environment.deploy.environment
  variable_name = each.key
  value         = each.value
}
