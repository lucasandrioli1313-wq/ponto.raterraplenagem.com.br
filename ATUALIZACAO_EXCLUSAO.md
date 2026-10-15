# Atualização: exclusão de funcionários

1. Faça backup do banco de dados Supabase antes da atualização.
2. Envie **app.py** e **templates/admin.html** deste pacote para os mesmos caminhos no repositório GitHub, mantendo os demais arquivos.
3. Faça commit na branch main e acompanhe o deploy no Render.
4. No painel /admin, em Usuários, clique em **Excluir cadastro** e confirme.
5. O funcionário perde o acesso e desaparece da lista de cadastros ativos. Os registros de ponto, fotos e relatórios históricos permanecem intactos.
6. Para desfazer, use **Restaurar cadastro** e depois **Ativar**.

A coluna `archived` é criada automaticamente na tabela `user` existente na primeira inicialização após a atualização. Nenhuma linha é excluída do banco.

**Importante:** excluir cadastro é exclusão lógica, não apagamento definitivo de dados pessoais. Estabeleça uma política de retenção e exclusão conforme a legislação aplicável.
