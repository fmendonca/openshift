#!/bin/bash
set -e

# Variáveis configuráveis
SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-}"
LOCATION="eastus"
RESOURCE_GROUP="aro-rg3"
CLUSTER_NAME="aro-cluster"
VERSION="4.17.27"                # versão específica disponível :contentReference[oaicite:4]{index=4}
VNET_NAME="aro-vnet"
VNET_ADDR="10.0.0.0/22"
MASTER_SUBNET_NAME="master-subnet"
MASTER_SUBNET_PREFIX="10.0.0.0/23"
WORKER_SUBNET_NAME="worker-subnet"
WORKER_SUBNET_PREFIX="10.0.2.0/23"
PULL_SECRET_FILE="pull-secret.txt"
REQUESTED_CORES=44              # Cores mínimos recomendados para ARO :contentReference[oaicite:5]{index=5}

# Configurar subscription, se necessário
if [[ -n "$SUBSCRIPTION_ID" ]]; then
  az account set --subscription "$SUBSCRIPTION_ID"
fi

# Login & garantir CLI mínima
az account show >/dev/null 2>&1 || az login
CLI_VER=$(az --version | head -n1 | awk '{print $2}')
echo "Azure CLI versão $CLI_VER"
# Criar resource group
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# Criar VNet e subnets
az network vnet create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$VNET_NAME" \
  --address-prefixes "$VNET_ADDR"

az network vnet subnet create \
  --resource-group "$RESOURCE_GROUP" \
  --vnet-name "$VNET_NAME" \
  --name "$MASTER_SUBNET_NAME" \
  --address-prefixes "$MASTER_SUBNET_PREFIX"

az network vnet subnet create \
  --resource-group "$RESOURCE_GROUP" \
  --vnet-name "$VNET_NAME" \
  --name "$WORKER_SUBNET_NAME" \
  --address-prefixes "$WORKER_SUBNET_PREFIX"

# Desativar network policies na subnet de controle
az network vnet subnet update \
  --resource-group "$RESOURCE_GROUP" \
  --vnet-name "$VNET_NAME" \
  --name "$MASTER_SUBNET_NAME" \
  --disable-private-link-service-network-policies true

# Criar cluster ARO com versão específica
az aro create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$CLUSTER_NAME" \
  --vnet "$VNET_NAME" \
  --master-subnet "$MASTER_SUBNET_NAME" \
  --worker-subnet "$WORKER_SUBNET_NAME" \
  --version "$VERSION" \
  --location "$LOCATION" \
  --pull-secret @"$PULL_SECRET_FILE"

# Mostrar detalhes do cluster
az aro show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$CLUSTER_NAME" \
  --output table

echo "Console do OpenShift:"
az aro show --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" --query "consoleProfile.url" -o tsv

echo "Senha kubeadmin:"
az aro list-credentials --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" --query kubeadminPassword -o tsv
