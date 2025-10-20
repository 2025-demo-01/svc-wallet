mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt
cat > k8s/base/secret.plain.yaml <<'YAML'
apiVersion: v1
kind: Secret
metadata:
  name: wallet-secret
  namespace: wallet
type: Opaque
stringData:
  HSM_ENDPOINT: "https://hsm.upx.exchange"
  HSM_API_KEY: "sophielog"
  HOT_WALLET_PASSWORD: "sophielog"
  DB_PASSWORD: "sophielog"
YAML
sops --encrypt --in-place k8s/base/secret.plain.yaml
mv k8s/base/secret.plain.yaml k8s/base/secret.enc.yaml
sops -d k8s/base/secret.enc.yaml | head -n 20
