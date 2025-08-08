terraform {
  required_providers {
    digitalocean = {
      source = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
   
  }
}

#Configure the DigitalOcean Provider
provider "digitalocean" {
  token = var.do_token
}


resource "digitalocean_droplet" "wazuh_server" {
    name = var.vm_name_wazuh
    image = var.image
    size = var.vm_wazuh_size
    region = var.region
    
    ssh_keys = [var.sshKey] 

    user_data = file("${path.module}/script/init.sh")


    connection {
    type        = "ssh"
    user        = "root"
    private_key = file(var.privateSshKey)
    host        = self.ipv4_address
  }

  provisioner "file" {
    source      = "${path.module}/script/wazuh.install.sh"
    destination = "/root/wazuh.install.sh"
  }


    tags = ["wazuh-server","devsecops"]
  
}


 resource "digitalocean_droplet" "tpot_server" {
  name = var.vm_tpot_name
  image = var.image
  size =  var.vm_tpot_size
  region = var.region


  ssh_keys = [var.sshKey ,var.privateSshToBackend] 
  user_data = file("${path.module}/script/init.sh")

  connection {
    type = "ssh"
    user = "root"
    private_key = file(var.privateSshKey)
    host = self.ipv4_address
  }

  provisioner "file" {
    source      = "${path.module}/script/tpot.install.sh"
    destination = "/root/tpot.install.sh"
  }

  tags = ["tpot-server","devsecops"]

}

 
 resource "digitalocean_droplet" "dvwa_server" {
  name = var.vm_dvwa_name
  image = var.image
  size =  var.vm_dvwa_size
  region = var.region

  ssh_keys = [var.sshKey ] 
  user_data = file("${path.module}/script/init.sh")

  connection {
    type = "ssh"
    user = "root"
    private_key = file(var.privateSshKey)
    host = self.ipv4_address
  }
  provisioner "file" {
    source      = "${path.module}/script/dvwa.install.sh"
    destination = "/root/dvwa.install.sh"
  }

  tags = ["dvwa-server","devsecops"]

}

 

# resource "null_resource" "provision_wazuh" {
#   depends_on = [digitalocean_droplet.wazuh_server]

#   connection {
#     type        = "ssh"
#     user        = "root"
#     private_key = file(var.privateSshKey)
#     host        = digitalocean_droplet.wazuh_server.ipv4_address
#   }

#   provisioner "file" {
#     source      = "${path.module}/script/wazuh.install.sh"
#     destination = "/root/wazuh.install.sh"
#   }

#   provisioner "file" {
#     source      = "${path.module}/script/check_wazuh_install.sh"
#     destination = "/root/check_wazuh_install.sh"
#   }

# provisioner "remote-exec" {
#   inline = [
#     "echo 'Starting Wazuh installation...'",
#     "chmod +x /root/wazuh.install.sh",
#     "nohup /root/wazuh.install.sh > /root/wazuh_install.log 2>&1 &",
#     "echo 'Installation started in background. Check /root/wazuh_install.log for progress.'"
#   ]
# }

# }
