output "github_environment" {
  description = "Select this environment on a future deployment job."
  value       = github_repository_environment.deploy.environment
}

output "oidc_subject" {
  description = "Exact GitHub subject trusted by the managed identity."
  value       = local.oidc_subject
}

output "azure_identity_id" {
  description = "Resource ID of the deployment managed identity."
  value       = azurerm_user_assigned_identity.deploy.id
}

output "github_environment_variables" {
  description = "Nonsecret Azure identifiers published as GitHub environment variables."
  value       = local.github_variables
}
