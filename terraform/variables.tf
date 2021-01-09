variable "storage_access_key" {
  type = string
}

variable "storage_secret_key" {
  type      = string
  sensitive = true
}
