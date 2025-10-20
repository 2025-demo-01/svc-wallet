# 1) age 키 생성 (로컬 1회)
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt

# 2) 환경 변수 등록
export SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt

# 3) 평문 시크릿 작성
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

# 4) 암호화
sops --encrypt --in-place k8s/base/secret.plain.yaml
mv k8s/base/secret.plain.yaml k8s/base/secret.enc.yaml

# 5) 복호화 테스트 (출력만 확인)
sops -d k8s/base/secret.enc.yaml | head -n 20
