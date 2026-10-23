# LexProof

Preservação e conferência de conversas do WhatsApp, com um **Relatório de
Preservação e Integridade** em PDF que qualquer pessoa pode verificar.

O LexProof guarda uma cópia exata dos arquivos recebidos, registra a impressão
digital (SHA-256) de cada um, obtém um carimbo de tempo de uma autoridade
independente e confere cada mensagem visível nos prints com a conversa
exportada do WhatsApp e com os demais prints.

> O relatório **não é** laudo pericial, ata notarial nem certificação de
> autenticidade. Ele registra o que foi recebido, quando, e o resultado das
> conferências, e permite que isso seja verificado de forma independente.

---

## Uso

```bash
./run.sh                 # abre o app
./run.sh pasta <pasta>   # preserva sem abrir a janela e abre o relatório
./run.sh testes          # testes automáticos
```

Opções de `./run.sh pasta`: `--sem-carimbo` (não usa a internet),
`--periodo 01/03/2026:30/04/2026`, `--descartar` (com `--periodo`, apaga o
restante da conversa) e `--conversa-toda` (transcreve a conversa inteira).

### No app

1. **Identifique o caso**: nome, responsável e como os arquivos chegaram
   (do próprio celular, do cliente por e-mail etc.).
2. **Adicione os arquivos** arrastando a pasta ou os arquivos. O app mostra o
   que reconheceu em cada um. Aceita:
   - o **ZIP de "Exportar conversa"** do WhatsApp (ou o `.txt`);
   - os **prints** da conversa;
   - um **print da tela de perfil do contato**, para ligar o nome ao número;
   - o **e-mail original (`.eml`)** com os prints ou o ZIP anexados.
3. **O que entra no relatório**: só as mensagens que aparecem nos prints
   (padrão), toda a conversa ou um período.
4. **Preserve**. Em menos de um minuto aparece o resultado em linguagem simples,
   com cada divergência apontada, e o PDF fica na pasta do caso
   (`~/.lexproof/cases/`).

---

## O que o app confere

| Conferência | Como |
|---|---|
| Integridade | Manifesto `preservacao/manifesto-sha256.txt` com o SHA-256 de cada arquivo recebido |
| Data | Carimbo de tempo RFC 3161 sobre o manifesto (FreeTSA; se falhar, DigiCert e depois Sectigo). Só o código do manifesto sai do computador |
| Origem por e-mail | Assinatura DKIM do provedor do remetente, conferida ao receber. A chave pública consultada fica arquivada dentro do carimbo |
| Prints × conversa | Cada balão é lido por OCR (texto, horário e separador de data, inclusive "Ontem" e dias da semana) e procurado na conversa exportada. São apontados texto, data ou hora diferentes, mensagem inexistente, contato diferente, ordem trocada, print anterior às mensagens e mensagens omitidas |
| Prints entre si | Os prints são costurados pelas mensagens repetidas entre um e outro: lacunas, contradições (mesma mensagem com texto diferente), contato e tamanho de imagem |
| Contato | O print do perfil liga o nome salvo na agenda ao número de telefone |
| Recorte de período | As mensagens do período são um bloco contínuo de linhas do `.txt`, copiado byte a byte e conferível contra o arquivo completo |

Tolerâncias da leitura: acentos, pontuação, uma letra trocada pelo OCR e
palavras grudadas não contam como diferença (ficam anotados). **Números
diferentes e palavras a mais, a menos ou trocadas sempre contam.** Um balão
cortado na borda do print é comparado com o trecho visível.

## Como qualquer pessoa confere uma preservação

Na pasta do caso:

```bash
sha256sum -c preservacao/manifesto-sha256.txt
cd preservacao
openssl ts -verify -data manifesto-sha256.txt -in manifesto-sha256.txt.tsr -CAfile freetsa_cacert.pem -untrusted freetsa_tsa.crt
```

O comando exato (muda conforme a autoridade usada) está em
`preservacao/COMO_VERIFICAR.txt` e na Seção 2 do relatório. Com recorte de
período, `preservacao/recorte.txt` traz o comando `sed -n 'A,Bp' ... | sha256sum`
que confere o recorte contra a conversa completa.

## O relatório

Capa com o resultado geral; resumo em cartões e "Como ler este relatório";
1. caso e origem dos arquivos (incluindo o e-mail e sua assinatura);
2. integridade e data (carimbo e como conferir);
3. conferência dos prints (contato, cada print com miniatura e resultado por mensagem, prints entre si);
4. mensagens (só as dos prints, salvo escolha em contrário);
5. metodologia aplicada (passo a passo, ferramentas e versões, o que permite e não permite afirmar, glossário e aviso);

e apêndices com todos os arquivos processados e o registro das etapas executadas.

## Privacidade

- Por padrão o relatório transcreve **só as mensagens que aparecem nos prints**.
- Com período, a conversa completa fica guardada lacrada na pasta do caso ou,
  se você escolher, é **apagada** (ficam só os hashes). O arquivo que você
  escolheu no computador nunca é apagado. O e-mail original é sempre mantido,
  porque é a prova da origem.
- A autoridade de carimbo recebe só o código do manifesto; o servidor de DNS,
  só o nome do domínio do e-mail.

## Orientações para quem envia os arquivos

- Exportar a conversa pelo WhatsApp ("Exportar conversa", sem mídia basta).
- Tirar os prints **sem nenhuma mensagem selecionada** (o fundo cinza da
  seleção atrapalha a leitura) e enviar os **arquivos originais**: por e-mail,
  como anexo, em lotes de até uns 20 prints (acima de 25 MB o Gmail troca os
  anexos por um link, que não fica coberto pela assinatura). **Não enviar pelo
  WhatsApp como foto**: isso recomprime a imagem e apaga a data do print.
- Quem recebe baixa o e-mail original (Gmail: ⋮ → Mostrar original → Baixar
  original) e arrasta o `.eml` para o app, sem encaminhar antes.

As mesmas orientações estão em "Como exportar a conversa do WhatsApp?" no app.

## Limitações conhecidas

- O app não atesta que o conteúdo é autêntico antes de ser entregue a ele: se a
  conversa exportada e os prints tivessem sido alterados juntos antes, a
  conferência não detectaria.
- O OCR lê o texto dos balões, não o conteúdo de fotos, áudios e vídeos.
- Mensagens **selecionadas** (fundo cinza) no print não são lidas.

---

## Instalação (BigLinux / Manjaro / Arch)

```bash
sudo pacman -S tesseract tesseract-data-por openssl
./bootstrap.sh     # cria o ambiente Python (.venv) e roda os testes
./run.sh
```

O `run.sh` chama o `bootstrap.sh` sozinho se o ambiente não existir e avisa se
faltar algum pacote do sistema. Requer Python 3.10 ou superior. O relatório usa
a fonte Noto Sans quando instalada (padrão no BigLinux) e, sem ela, Helvetica.

## Estrutura

```
lexproof/
├── ui/simple_window.py      # janela do app (três telas)
├── pipeline/preservation.py # etapas da preservação, em ordem
├── acquisition/             # ZIP, e-mail (DKIM), recorte de período
├── crypto/                  # SHA-256 e selo (manifesto + carimbo)
├── blockchain/rfc3161.py    # carimbo de tempo RFC 3161 e certificados das autoridades
├── parsers/                 # leitura da conversa exportada do WhatsApp
├── triangulation/           # leitura dos prints, conferência, costura, perfil do contato
├── reports/                 # relatório PDF
└── utils/intake.py          # identificação dos arquivos adicionados
arquivo-morto/               # código e documentos antigos (ver o README de lá)
```

Mais detalhes das mudanças em [CHANGELOG.md](CHANGELOG.md).

## Licença

MIT. Veja [LICENSE](LICENSE).
