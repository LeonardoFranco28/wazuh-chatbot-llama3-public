# Set the variable value in *.tfvars file

variable "do_token" {
  description = "DigitalOcean API token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "DigitalOcean region for the VPC"
  type        = string
  default     = "nyc1"
}

variable "vpc_ip_range" {
  description = "IP range for the VPN"
  type        = string
  default     = "10.0.0.0/16"
}

variable "vpc_name" {
  description = "Name of the VPC"
  type        = string
  default     = "ia-networking-vpc"
}

variable "vm_name_wazuh" {
  description = "Name of the Wazuh VM"
  type        = string
  default     = "ia-wazuh-vm"
}

variable "vm_name_wazuh_agent" {
  description = "Name of the Wazuh Agent VM"
  type        = string
}

variable "vm_wazuh_size" {
  description = "Size of the Wazuh VM"
  type        = string
  default     = "s-1vcpu-1gb"
}

variable "vm_wazuh_image" {
  description = "Image of the Wazuh VM"
  type        = string
  default     = "ubuntu-24-04-x64"
}

variable "vm_tpot_name" {
  description = "Name of the SOAR VM"
  type        = string
  default     = "tpot-vm"
}

variable "vm_tpot_size" {
  description = "Size of the SOAR VM"
  type        = string
  default     = "s-2vcpu-4gb"
}

variable "image" {
  description = "Image of the SOAR VM"
  type        = string
  default     = "ubuntu-24-04-x64"
}

variable "vm_dvwa_size" {
  description = "Size of the DVWA VM"
  type        = string
  default     = "s-4vcpu-8gb"
}
variable "vm_dvwa_image" {
  description = "Image of the DVWA VM"
  type        = string
  default     = "ubuntu-24-04-x64"
}

variable "vm_dvwa_name" {
  description = "Name of the DVWA VM"
  type        = string
  default     = "dvwa-server"
}

variable "sshKey" {
  description = "SSH key of the Wazuh VM"
  type        = string
  sensitive   = true
}

variable "privateSshKey" {
  description = "Private SSH key of the Wazuh VM"
  type        = string
  sensitive   = true
}

variable "privateSshToBackend" {
  description = "SSH key of the Wazuh VM"
  type        = string
  sensitive   = true
  default     = "app/backend/.ssh/key.pub"
}

variable "vpc_uuid" {
  description = "UUID of the VPC"
  type        = string
} 

