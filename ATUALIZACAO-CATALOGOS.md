# Atualização diária dos catálogos

Para atualizar os preços/estoques, substitua as três planilhas pelos arquivos mais recentes, mantendo estes nomes:

- \`catalog-input/EMS.xlsx\`
- \`catalog-input/BIOLAB.xlsx\`
- \`catalog-input/NOVA_QUIMICA.xlsx\`

Faça upload das três na mesma alteração do GitHub (Add file → Upload files) e confirme o commit na branch \`main\`. O workflow **Atualizar catálogos Oriente Farma** processa as planilhas, atualiza EMS, Biolab e Nova Química e mantém as demais marcas, incluindo Sandoz. Se alguma planilha estiver faltando ou inválida, a publicação é interrompida.

Depois de conectar este repositório ao Cloudflare Pages via integração Git, cada commit atualizado publica o site automaticamente. O app continua usando o telefone de pedidos configurado no código.
