# Este código es compatible con Terraform 4.25.0 y versiones compatibles con 4.25.0.
# Para obtener información sobre la validación de este código de Terraform, consulta https://developer.hashicorp.com/terraform/tutorials/gcp-get-started/google-cloud-platform-build#format-and-validate-the-configuration

terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "6.10.0"
    }
  }
}

provider "google" {
  project = "YOUR_PROJECT_ID"
  region = "us-central1"
}


resource "google_compute_instance" "ai" {
  boot_disk {
    auto_delete = true
    device_name = "ai"

    initialize_params {
      image = "projects/ubuntu-os-cloud/global/images/ubuntu-2404-noble-amd64-v20250725"
      size  = 50
      type  = "pd-balanced"
    }

    mode = "READ_WRITE"
  }

  can_ip_forward      = false
  deletion_protection = false
  enable_display      = false

  labels = {
    goog-ec-src           = "vm_add-tf"
    goog-ops-agent-policy = "v2-x86-template-1-4-0"
  }

  machine_type = "t2d-standard-8"

  metadata = {
    enable-osconfig = "TRUE"
    ssh-keys        = "YOUR_SSH_KEY_PUBLIC"
    startup-script  = "sudo apt-get update -y"
  }

  name = "ai"

  network_interface {
    access_config {
      network_tier = "PREMIUM"
    }

    queue_count = 0
    stack_type  = "IPV4_ONLY"
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    preemptible         = false
    provisioning_model  = "STANDARD"
  }

  

  shielded_instance_config {
    enable_integrity_monitoring = true
    enable_secure_boot          = false
    enable_vtpm                 = true
  }

  tags = ["http-server", "https-server"]
  zone = "us-central1-a"
}

module "ops_agent_policy" {
  source          = "github.com/terraform-google-modules/terraform-google-cloud-operations/modules/ops-agent-policy"
  project         = "cellular-syntax-468023-j1"
  zone            = "us-central1-f"
  assignment_id   = "goog-ops-agent-v2-x86-template-1-4-0-us-central1-f"
  agents_rule = {
    package_state = "installed"
    version = "latest"
  }
  instance_filter = {
    all = false
    inclusion_labels = [{
      labels = {
        goog-ops-agent-policy = "v2-x86-template-1-4-0"
      }
    }]
  }
}
