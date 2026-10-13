# R.A. Terraplenagem — Relógio Ponto (protótipo operacional)

Sistema Flask com dois perfis, fotos de rosto e máquina em cada marcação, GPS com consentimento no momento da marcação, horário do servidor, relatórios mensais e CSV.

## Rodar localmente

```bash
python -m venv .venv
# Ative o ambiente virtual
pip install -r requirements.txt
# Defina SECRET_KEY e ADMIN_PASSWORD (senha forte) no ambiente
python app.py
```

Acesse `http://localhost:5000/login`. A conta `admin` é criada no primeiro início quando `ADMIN_PASSWORD` está configurada. Depois, cadastre os funcionários pelo painel. Nunca publique sem definir `SECRET_KEY` e `ADMIN_PASSWORD`.

## Publicar no Render

1. Envie a pasta para um repositório **privado** no GitHub.
2. No Render: **New → Blueprint**, selecione o repositório e aplique `render.yaml`.
3. Informe uma senha administrativa forte na variável `ADMIN_PASSWORD` e confirme `SECRET_KEY` gerada.
4. A implantação usa **Starter com disco persistente** em `/var/data`, necessário para preservar SQLite e as fotos. **Não use o plano gratuito**, pois o armazenamento local pode ser perdido. Disco persistente e hospedagem têm custos.
5. Quando o serviço estiver Live, abra **Settings → Custom Domains** e adicione `ponto.raterraplenagem.com.br`.
6. No editor DNS atual de `raterraplenagem.com.br`, crie um `CNAME` com host `ponto` apontando para o endereço `seu-servico.onrender.com` **exato** exibido no Render. Não altere os registros do site principal.
7. Aguarde a validação DNS e o HTTPS. Teste câmera e localização no celular. O login redireciona o administrador para `/admin` e funcionários para `/funcionario`.

## Limites e cuidados antes do uso oficial

- É uma **primeira versão funcional**, não um REP-P homologado ou comprovadamente conforme à Portaria MTP 671/2021. Não substitua o registro legal de jornada sem revisão técnica e jurídica.
- O registro usa hora do servidor em UTC e apresenta horário de Brasília. GPS depende da permissão do navegador e não impede falsificação de localização. Fotos não fazem reconhecimento facial biométrico.
- A administração vê as marcações após serem gravadas; **não há notificações por WhatsApp/e-mail nem rastreamento contínuo**.
- Fotos são acessíveis apenas ao administrador autenticado. Os dados pessoais exigem política de retenção, acesso restrito, informação aos trabalhadores e conformidade com a LGPD.
- Faça backups do banco SQLite **e** da pasta `/var/data/uploads` em armazenamento externo. Disco persistente não substitui backup.
- Para produção ampliada: migrar para PostgreSQL, armazenar imagens em storage privado, acrescentar trilha de auditoria, recuperação de senhas, rate limiting, proteção contra CSRF em APIs e relatórios de jornada trabalhada (intervalos/horas extras).
- **Não escale para várias instâncias com SQLite**. Esta configuração foi projetada para uma instância.
