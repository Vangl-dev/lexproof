# Arquivo morto

Arquivos retirados do LexProof em 23/10/2026, quando a interface nova e o
relatório redesenhado passaram a ser o caminho único do aplicativo. Nada aqui é
usado pelo app nem pelos testes. Fica guardado para consulta.

Os arquivos de código e documentação foram movidos com `git mv`, então o
histórico de cada um continua disponível (`git log --follow <arquivo>`).

## O que tem aqui

| Pasta | Conteúdo | Por que saiu |
|---|---|---|
| `codigo/lexproof/ui/` | Interface antiga (janela com abas e menus, 20 widgets, diálogos, ícones, temas) | Substituída por `lexproof/ui/simple_window.py` |
| `codigo/lexproof/analysis/` | "Smart Analysis" | Só a interface antiga usava |
| `codigo/lexproof/crypto/manifest.py` | Manifesto JSON antigo | Substituído pelo selo (`lexproof/crypto/seal.py`), conferível com `sha256sum -c` |
| `codigo/lexproof/blockchain/` | OpenTimestamps e gerenciador de âncoras | Não funcionavam e não eram chamados; o carimbo de tempo é o RFC 3161 |
| `codigo/lexproof/reports/` | Relatórios HTML, JSON, ZIP, manifesto e QR code | Não eram gerados por nenhum fluxo |
| `codigo/lexproof/perceptual/`, `timeline/comparator.py` | Hash perceptual, comparador de linhas do tempo | Sem uso; a conferência dos prints faz esse papel |
| `codigo/lexproof/utils/`, `verification/reporter.py` | Dados de demonstração, configuração de log, relatório de verificação | Sem uso |
| `testes/` | Testes do código acima | Testavam só o que foi arquivado |
| `docs/` | Documentos de estado de julho de 2026 (arquitetura, homologação, plano de testes, roadmap etc.) e os modelos genéricos `CONTRIBUTING.md` e `SECURITY.md` | Desatualizados ou com afirmações que não correspondiam ao app; o estado atual está no `README.md` da raiz e no `CHANGELOG.md` |
| `scripts/` | Scripts de teste avulsos da raiz | Substituídos por `./run.sh` |
| `demo/` | Demonstração da versão 0.5 | Usava o "Smart Analysis" |
| `imagens/` | Capturas de tela da interface antiga e o ícone | Não versionadas (fora do git) |
| `saidas-antigas/` | PDFs gerados entre julho e setembro de 2026 | Não versionadas (fora do git): podem conter dados de conversas reais |

## Para trazer algo de volta

Mova o arquivo de volta para o caminho original (o mesmo, sem o prefixo
`arquivo-morto/codigo/`). A interface antiga, por exemplo, dependia de
`lexproof/ui/main_window.py`, `lexproof/ui/widgets/`, `lexproof/ui/dialogs/`,
`lexproof/ui/icons.py` e `lexproof/ui/styles/`, e era aberta com
`lexproof --classico` (opção removida de `lexproof/core/application.py`).
