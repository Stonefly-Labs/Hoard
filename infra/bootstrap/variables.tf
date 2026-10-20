variable "subscription_id" {
  description = "Explicit Azure subscription UUID. Never inferred by the bootstrap."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "subscription_id must be an Azure subscription UUID."
  }
}

variable "location" {
  description = "Azure region chosen by the operator for the dedicated resource group and identity."
  type        = string

  validation {
    condition     = length(trimspace(var.location)) > 0
    error_message = "Choose a nonempty Azure region."
  }
}

variable "environment" {
  description = "The single GitHub deployment environment; must match future workflow environment names."
  type        = string
  default     = "dev"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,30}$", var.environment))
    error_message = "Use 1-31 lowercase letters, digits, or hyphens, beginning with a letter."
  }
}

variable "github_owner" {
  description = "GitHub organization/user owning the repository. Case must match the OIDC subject."
  type        = string
  default     = "Stonefly-Labs"
}

variable "github_repository" {
  description = "Repository name without owner. Case must match the OIDC subject."
  type        = string
  default     = "Hoard"
}
