mock_provider "azurerm" {
  mock_resource "azurerm_resource_group" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-hoard-dev"
    }
  }
  mock_resource "azurerm_user_assigned_identity" {
    defaults = {
      id           = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-hoard-dev/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-hoard-dev-github"
      principal_id = "00000000-0000-0000-0000-000000000002"
      client_id    = "00000000-0000-0000-0000-000000000003"
      tenant_id    = "00000000-0000-0000-0000-000000000004"
    }
  }
}
mock_provider "github" {}

variables {
  subscription_id = "00000000-0000-0000-0000-000000000001"
  location        = "eastus"
}

run "environment_bound_identity" {
  command = apply

  assert {
    condition     = azurerm_federated_identity_credential.github.subject == "repo:Stonefly-Labs/Hoard:environment:dev"
    error_message = "OIDC must be bound to the exact repository environment, not a branch wildcard."
  }

  assert {
    condition     = azurerm_federated_identity_credential.github.issuer == "https://token.actions.githubusercontent.com" && azurerm_federated_identity_credential.github.audience == tolist(["api://AzureADTokenExchange"])
    error_message = "Use the GitHub issuer and Azure token exchange audience."
  }

  assert {
    condition     = azurerm_role_assignment.deploy.scope == azurerm_resource_group.deploy.id && azurerm_role_assignment.deploy.role_definition_name == "Contributor"
    error_message = "Deployment permission must remain Contributor at resource-group scope."
  }

  assert {
    condition     = github_repository_environment.deploy.deployment_branch_policy[0].custom_branch_policies && !github_repository_environment.deploy.deployment_branch_policy[0].protected_branches && github_repository_environment_deployment_policy.main.branch_pattern == "main"
    error_message = "Only main may use the environment; release tags and PR branches do not deploy."
  }

  assert {
    condition     = github_actions_environment_variable.azure["AZURE_CLIENT_ID"].value == azurerm_user_assigned_identity.deploy.client_id && github_actions_environment_variable.azure["AZURE_TENANT_ID"].value == azurerm_user_assigned_identity.deploy.tenant_id && github_actions_environment_variable.azure["AZURE_SUBSCRIPTION_ID"].value == var.subscription_id
    error_message = "GitHub OIDC variables must refer to the actual deployment identity and subscription."
  }
}

run "renamed_environment" {
  command = apply

  variables {
    environment       = "sandbox"
    github_owner      = "Example"
    github_repository = "Cache"
  }

  assert {
    condition     = azurerm_federated_identity_credential.github.subject == "repo:Example/Cache:environment:sandbox" && github_repository_environment.deploy.environment == "sandbox"
    error_message = "Changing repository/environment must update trust and GitHub configuration together."
  }
}
