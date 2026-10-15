# Atualização V5 — relatórios e bloqueio progressivo

Substitua `app.py` e `templates/admin.html` no GitHub. Faça backup do Supabase antes da atualização.

- `/admin/relatorio.csv`: uma linha por funcionário por dia, incluindo dias sem marcação, com horários e duração HH:MM:SS.
- `/admin/relatorios-por-funcionario.zip`: um CSV por funcionário, todos os dias do mês. CSV não suporta múltiplas abas; use os arquivos separados do ZIP no Excel.
- Tentativas incorretas de senha de funcionários: 1 a 5 sem espera; 6ª espera 30 segundos; 7ª espera 60 segundos; 8ª espera 120 segundos; 9ª bloqueia até liberação administrativa. Tentativas durante a espera não contam. Sucesso zera o contador.
- Administrador: botão Desbloquear login na lista de funcionários.
- Registros incompletos são marcados para conferência; duração soma pares entrada/saída. Turnos que cruzam meia-noite são distribuídos por dia.
- Recomendação: conferir horas, ajustes manuais e conformidade trabalhista antes de utilizar como espelho de ponto oficial.
