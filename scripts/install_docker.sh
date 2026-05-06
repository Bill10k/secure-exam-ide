#!/bin/bash
# install_docker.sh
# Script to install Docker Engine on Ubuntu
# Requires sudo privileges

echo "Updating package index..."
sudo apt-get update

echo "Installing prerequisites..."
sudo apt-get install -y ca-certificates curl

echo "Adding Docker's official GPG key..."
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo "Adding Docker repository to Apt sources..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "Updating package index again..."
sudo apt-get update

echo "Installing Docker Engine, CLI, and Containerd..."
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "Adding current user to the docker group..."
if [ -n "$SUDO_USER" ]; then
  sudo usermod -aG docker $SUDO_USER
else
  sudo usermod -aG docker $USER
fi

echo "Docker installation complete!"
echo "Please log out and log back in, or run 'newgrp docker' to apply group changes."
