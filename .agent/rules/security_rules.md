# Güvenlik Kuralları — DUS Mentörü

> Bu kurallar sistemin güvenliğini korur. Asla ihlal edilmez.

## 🔴 Mutlak Yasaklar

1. `.env` dosyasını okuma, yazma, silme veya içeriğini chat'e yansıtma
2. API anahtarlarını kod içine gömme (hardcode)
3. Veri silme komutları çalıştırma (Pinecone `delete_all`, Supabase `DROP TABLE`)
4. Furkan'ın onayı olmadan terminal komutu çalıştırma
5. `rm -rf` veya benzeri yıkıcı sistem komutları

## 🟡 Güvenlik Kontrol Listesi (Yeni Script Yazarken)

- [ ] API anahtarları `os.environ` üzerinden mi alınıyor?
- [ ] `load_dotenv()` dosyanın başında mı?
- [ ] Hassas veri loglanıyor mu? (Eğer evet → kaldır)
- [ ] Rate limit koruması var mı? (retry/sleep)
- [ ] Exception handling eksiksiz mi?

## 🟢 .gitignore Zorunlu İçerik

```gitignore
.env
__pycache__/
*.pyc
*.pyo
tmp/
*.log
.DS_Store
```

## Supabase Güvenliği

- RLS (Row Level Security) politikaları sorgulanmadan veri değiştirme
- `service_role` key'i sadece backend'de, `anon` key'i asla kullanma
- SQL injection'a karşı parametreli sorgular kullan

## Pinecone Güvenliği

- `PINECONE_API_KEY` `.env`'de, `os.environ` üzerinden oku
- Index silme işleminden önce Furkan'dan yazılı onay al
- `deletion_protection` disabled olan index'lere dikkat et
