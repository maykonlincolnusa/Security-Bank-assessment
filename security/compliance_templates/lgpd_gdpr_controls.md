# LGPD/GDPR - Controles Minimos de Privacidade e Compliance

## Governanca
- Definir controlador e operador por fluxo de dados.
- Manter registro de atividades de tratamento (ROPA).
- Definir base legal por tipo de dado (consentimento, legitimo interesse, obrigacao legal, etc.).
- Nomear responsavel de privacidade/DPO quando aplicavel.

## Data minimization e purpose limitation
- Coletar somente campos estritamente necessarios para o Trust Score.
- Proibir coleta de dados sensiveis sem base legal especifica.
- Vincular cada campo a uma finalidade documentada e revisada.

## Direitos do titular (LGPD/GDPR)
- Acesso: fornecer extrato de dados tratados.
- Correcao: corrigir dados imprecisos em SLA definido.
- Exclusao (right to erasure): excluir ou anonimizar quando permitido legalmente.
- Portabilidade: exportar dados em formato estruturado.
- Oposicao/restricao: suspender processamento quando aplicavel.

## Seguranca da informacao
- Criptografia em transito (TLS) e em repouso (KMS).
- RBAC + least privilege para dados e modelos.
- Logs de auditoria com who/what/when.
- Segregacao de ambientes (dev/stage/prod).

## Retencao e descarte
- Definir politica de retencao por categoria de dado.
- Automatizar descarte seguro (delete/anonimizacao) apos prazo.
- Registrar justificativa de retencao estendida quando houver obrigacao legal.

## Compartilhamento e terceiros
- Firmar DPA/contrato com subprocessadores.
- Restringir transferencia internacional conforme marco legal aplicavel.
- Avaliar impacto (DPIA/LIA) para processamentos de alto risco.

## Incidentes e notificacao
- Playbook de resposta a incidente com SLA.
- Notificacao a autoridade e titulares conforme lei aplicavel.
- Evidencias de investigacao e medidas corretivas.

## IA responsavel
- Documentar vieses e limitacoes de modelo.
- Proibir decisao automatizada exclusiva para medidas regulatorias sem revisao humana.
- Manter explicabilidade e trilha de decisao.
