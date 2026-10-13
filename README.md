# R.A. Relógio Ponto — Render Free + Supabase

## 1. Criar armazenamento no Supabase
1. Crie projeto em https://supabase.com/dashboard (plano Free, se disponível).
2. Em **Storage → New bucket**, crie `ponto-fotos` e deixe **Public desativado**.
3. Em **Connect**, copie a string de conexão **Session pooler** do PostgreSQL. Substitua `[YOUR-PASSWORD]` pela senha do banco, codificando caracteres especiais em URL (por exemplo `@` vira `%40`). A string deve começar por `postgresql://`.
4. Em **Project Settings → API Keys**, copie a chave **service_role** (ou secret key compatível com o endpoint Storage). **Nunca coloque essa chave no frontend, no GitHub ou em screenshots.**
5. Copie a **Project URL** em **Project Settings → API**.

## 2. GitHub
Envie o conteúdo desta pasta para a **raiz** de um repositório privado (app.py, render.yaml, requirements.txt, templates/ e static/ no mesmo nível). Se mantiver esta pasta como subpasta, use `RA_Ponto_Render_Gratis/render.yaml` como Blueprint Path e ajuste os comandos de build/start para a subpasta; mais simples é usar a raiz.

## 3. Render
1. **New → Blueprint** e selecione o repositório/branch `main`.
2. **Blueprint Path:** `render.yaml` (NÃO `app.py`).
3. Confira `plan: free` e **nenhum** recurso disk/database pago.
4. Configure `ADMIN_PASSWORD` (senha forte), `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` no Render. `SECRET_KEY` é gerada automaticamente.
5. Aplique e aguarde o deploy. Se a conta exigir cartão mesmo no plano Free, não prossiga sem verificar a cobrança/limites; a plataforma pode ter exigências de verificação.
6. Teste login, cadastro, ponto e fotos. Depois configure o domínio `ponto.raterraplenagem.com.br` no serviço e CNAME `ponto` no DNS apontando para o hostname `.onrender.com` indicado pelo Render.

## Avisos importantes
- **Protótipo para testes, não homologado como REP-P.** Valide legislação trabalhista, LGPD, política de retenção, backups, controle de acesso e auditoria antes de uso oficial.
- O Render Free pode hibernar após 15 minutos sem tráfego, atrasando a primeira marcação. Pode ser suspenso por limites de uso.
- O Supabase Free pode pausar projetos inativos e possui cotas de banco, armazenamento e tráfego. Faça backups externos periódicos e monitore uso.
- As fotos são privadas no bucket e só passam pelo servidor para administradores autenticados. Não exponha a service_role.
- GPS exige HTTPS e permissão do usuário. O horário é atribuído pelo servidor, não pelo telefone.
- O banco e o armazenamento precisam ser criados ANTES do deploy. Nunca use SQLite local para dados reais no Render Free.
