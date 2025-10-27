# KCP 인증서를 AWS Parameter Store에 추가하는 스크립트
# 암호화된 개인 키를 AWS Parameter Store에 안전하게 저장

Write-Host "🔧 AWS Parameter Store에 KCP 인증서 추가 중..." -ForegroundColor Green

# 암호화된 개인 키를 AWS Parameter Store에 추가 (SecureString)
aws ssm put-parameter `
    --name "/snspmt/KCP_CERT_INFO" `
    --value "-----BEGIN ENCRYPTED PRIVATE KEY-----
MIICrjAoBgoqhkiG9w0BDAEDMBoEFA1PchZtKTQCGZNRvK10J8ZYa0AhAgIIAASC
AoAxffS8YSxZvVQ1i5IdYnT523OHJ0G6WxxpLI6NUHz3K/DZVEVHgPtWAXN6shDn
IgYPLgvg3QplU4VETCGIUILu4jRJX02SztOzy+D5sB+lrxGkgzHCsb6he/mMvEft
kBSL1F95FtFhcDAlLYwsvKCwYXVbu+4sP8fRaXEk7XX4AJEzEKU2YPcfKItRLAvS
helGRk0NN9oQwuCb+TkD19FRqGKXryGwgyAGf2oEm4fPzooJQeiYEtRnFmODX86K
rfhNb+S+Gr3+DHdUhOBc/IcF4KwtWMwghKiqK1SVPqgkd8UT6OP8gpjQ0JlBXVyj
XnjHD1zQ3nQTjXinfOo14lerPA4saN3mHL99akbCNyjo5bVoaWYGpz5dBa7ZucwL
SUSjHfxK9enPmWmFOR4B4xbta/91u8/1QDQigsa+m8LvinFv6EIDwaIgD6QcdW5r
tbcxQ/Ky5DAc/phlSLYIu8l8I4OAsGVZ5YouY7AIvMXhKaajSeOPEnI5mqNkUbpa
159r4Ek1/Z0w9YJV+0ZjWiU4GQbdXfqZqVqbNlKU5wAeTh4e8eb1ewGj6xxbgSn2
y+mEaJHZoIYl4v5u0ymoHVHLDrUGQAclGFQAz6H5xxI81Zl9roj1J9g9R1CTtF4o
TvmoWajtzLTNG7aYdihveKG5G7uddBg+vTSiC+WeDppBkp8L0fA/lUwyF5YV7kIT
3Hl003LT1+ByP0u3rEs1vH0PhEBYQTn8AF5Pp3BKvHtsjm/y7GB0Nn01qnJA5HDr
hx6v0f8JwL7C4f5Fyc44dKuiAJk8RhGQwgN2KHCtif/5QavE2Gizx5o7aRmE+90m
cnG0kRnEuRcCLPVo2Y3l/YOS
-----END ENCRYPTED PRIVATE KEY-----" `
    --type "SecureString" `
    --description "KCP 암호화된 개인 키" `
    --overwrite

# KCP 인증서 비밀번호를 AWS Parameter Store에 추가 (SecureString)
aws ssm put-parameter `
    --name "/snspmt/KCP_CERT_PASSWORD" `
    --value "Thtufflxl01!" `
    --type "SecureString" `
    --description "KCP 인증서 비밀번호" `
    --overwrite

Write-Host "✅ KCP 인증서 추가 완료!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 추가된 파라미터:" -ForegroundColor Yellow
Write-Host "- /snspmt/KCP_CERT_INFO (암호화된 개인 키)"
Write-Host "- /snspmt/KCP_CERT_PASSWORD (비밀번호)"
Write-Host ""
Write-Host "⚠️  이제 백엔드 코드가 AWS Parameter Store에서 인증서를 읽어옵니다."

