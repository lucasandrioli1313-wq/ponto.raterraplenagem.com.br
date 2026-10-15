# Atualização de login e senhas — R.A. Terraplenagem

- O nome de usuário no login não diferencia maiúsculas/minúsculas. Ex.: JOAO = joao.
- O cadastro de novos nomes de usuário também verifica duplicidade sem diferenciar maiúsculas/minúsculas.
- A senha continua diferenciando maiúsculas/minúsculas e nunca é exibida, pois é armazenada em hash.
- O administrador pode definir uma nova senha (mínimo 10 caracteres) para cada funcionário ativo ou inativo não arquivado.
- Nenhum registro de ponto, GPS ou foto é apagado.

## Instalação

No GitHub, substitua **app.py** e **templates/admin.html** pelos arquivos desta versão. Faça commit na branch main. Aguarde o deploy do Render e teste com um funcionário de teste. Faça backup antes de atualizar. Não substitua variáveis secretas do Render.
