// [Complemento da plataforma] Progresso gravável e ferramentas integradas.
// Conversa com scripts/portal_api.py (porta 8001). Sem a API, o site continua legível.
(() => {
  const API = `${location.protocol}//${location.hostname}:8001/api`;
  const raiz = document.querySelector('script[src$="assets/portal.js"]').src.replace(/assets\/portal\.js.*$/, "");
  const pad = (n) => String(n).padStart(2, "0");
  const quando = (ts) => ts ? new Date(ts).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "";
  const el = (tag, attrs = {}, ...filhos) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) k === "class" ? (e.className = v) : e.setAttribute(k, v);
    for (const f of filhos) if (f != null) e.append(f);
    return e;
  };

  async function carregar() {
    const r = await fetch(`${API}/progresso`);
    if (!r.ok) throw new Error(r.status);
    return r.json();
  }

  // Login automático: a API devolve o token do Jupyter e grava o cookie de sessão do MinIO
  // (cookies valem por host, então o console em localhost:<porta> já abre logado).
  let tokenJupyter = "";
  async function iniciarSessao() {
    try {
      const r = await fetch(`${API}/sessao`, { method: "POST", credentials: "include" });
      if (r.ok) tokenJupyter = (await r.json()).jupyter_token || "";
    } catch { /* sem sessão: as ferramentas pedem login normalmente */ }
  }
  const comToken = (url) => (tokenJupyter ? `${url}?token=${encodeURIComponent(tokenJupyter)}` : url);

  async function gravar(pedido) {
    const r = await fetch(`${API}/estudo`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(pedido),
    });
    if (!r.ok) throw new Error(r.status);
    return r.json();
  }

  // Estado de uma aula: concluída / em andamento / não iniciada (+ alerta se algum check falha)
  function situacao(a, totalCriterios) {
    const marcados = Object.keys(a.criterios).length;
    const c = a.checks;
    if (a.concluida_em) return { cls: "ok", txt: "Concluída" };
    if (c.declarados && c.passou === c.declarados && (!totalCriterios || marcados >= totalCriterios))
      return { cls: "pronta", txt: "Pronta para concluir" };
    if (marcados || c.ultima) return { cls: "andamento", txt: "Em andamento" };
    return { cls: "nada", txt: "Não iniciada" };
  }

  function barra(valor, total) {
    const pct = total ? Math.round((100 * valor) / total) : 0;
    return el("span", { class: "rl-barra", title: `${valor}/${total}` }, el("span", { style: `width:${pct}%` }));
  }

  function textoChecks(c) {
    if (!c.declarados) return "sem checks automáticos";
    if (!c.ultima) return `0/${c.declarados} · ainda não executados`;
    return `${c.passou}/${c.declarados} passando${c.falhou ? ` · ${c.falhou} falhando` : ""} · ${quando(c.ultima)}`;
  }

  function aviso(destino, msg) {
    destino.replaceChildren(el("p", { class: "rl-aviso" }, msg));
  }

  // ------------------------------------------------------------------ página da aula
  function chaveItem(li) {
    const copia = li.cloneNode(true);
    copia.querySelectorAll("ul, ol").forEach((x) => x.remove());
    return copia.textContent.replace(/\s+/g, " ").trim();
  }

  function paginaAula(painel, dados) {
    const n = painel.dataset.aula;
    const a = dados.aulas[n];
    const caixas = [...document.querySelectorAll(".task-list-item input[type=checkbox]")];
    const atual = { ...a };

    // Situação da aula: topo da barra da esquerda (acima da navegação).
    // Ações: topo da coluna da direita (acima do índice). Em telas estreitas e na tela
    // dividida as barras somem, então o mesmo painel aparece dentro do conteúdo (CSS decide).
    const lateral = (seletor, classe) => {
      const alvo = document.querySelector(seletor);
      if (!alvo) return null;
      const caixa = el("div", { class: `rl-lateral md-typeset ${classe}` }); // md-typeset: estilo dos botões do tema
      alvo.parentElement.insertBefore(caixa, alvo);
      return caixa;
    };
    // Fora da área que rola: a barra rola sozinha até a aula atual e esconderia o bloco
    const ladoStatus = lateral(".md-sidebar--primary .md-sidebar__scrollwrap", "rl-lateral--status");
    const ladoAcoes = lateral(".md-sidebar--secondary .md-sidebar__scrollwrap", "rl-lateral--acoes");

    const blocoStatus = () => {
      const marcados = caixas.filter((c) => c.checked).length;
      const s = situacao(atual, caixas.length);
      const itens = Object.entries(atual.checks.itens).map(([id, st]) =>
        el("code", { class: `rl-chip rl-${st}`, title: st }, `${st === "passou" ? "✓" : st === "falhou" ? "✗" : "–"} ${id}`));
      return el("div", { class: "rl-bloco" }, ...[
        el("div", { class: "rl-cab" },
          el("span", { class: `rl-status rl-${s.cls}` }, s.txt),
          atual.concluida_em ? el("span", { class: "rl-dica" }, `em ${quando(atual.concluida_em)}`) : null),
        el("div", { class: "rl-linha" }, el("strong", {}, "Checks: "), textoChecks(atual.checks)),
        itens.length ? el("div", { class: "rl-chips" }, ...itens) : null,
        caixas.length ? el("div", { class: "rl-linha" }, el("strong", {}, "Critérios: "),
          `${marcados}/${caixas.length} `, barra(marcados, caixas.length)) : null,
      ].filter(Boolean));
    };

    const blocoAcoes = () => {
      const dividido = document.documentElement.classList.contains("rl-split");
      const dividir = el("button", { class: "md-button md-button--primary" },
        dividido ? "Fechar notebook" : "Estudar com notebook");
      dividir.onclick = () => { telaDividida(n, dados); render(); };
      const concluir = el("button", { class: "md-button" },
        atual.concluida_em ? "Desmarcar conclusão" : "Marcar aula como concluída");
      concluir.onclick = async () => {
        concluir.disabled = true;
        try { Object.assign(atual, await gravar({ aula: +n, concluida: !atual.concluida_em })); }
        catch { alert("Não consegui gravar: a API de progresso está no ar?"); }
        render();
      };
      const acoes = [dividir, concluir];
      if (painel.dataset.onde === "container") {
        const alvo = painel.dataset.lab ? `#jupyter=${encodeURIComponent(painel.dataset.lab)}` : "#jupyter";
        acoes.push(el("a", { class: "md-button", href: `${raiz}ambiente.html${alvo}` }, "Abrir arquivo da aula"));
      }
      return el("div", { class: "rl-acoes" }, ...acoes);
    };

    const render = () => {
      ladoStatus?.replaceChildren(blocoStatus());
      ladoAcoes?.replaceChildren(blocoAcoes());
      painel.replaceChildren(blocoStatus(), blocoAcoes());
    };

    for (const caixa of caixas) {
      const chave = chaveItem(caixa.closest(".task-list-item"));
      caixa.disabled = false;
      caixa.checked = !!atual.criterios[chave];
      caixa.addEventListener("change", async () => {
        try {
          Object.assign(atual, await gravar({ aula: +n, criterio: chave, marcado: caixa.checked }));
        } catch {
          caixa.checked = !caixa.checked;
          alert("Não consegui gravar: a API de progresso está no ar?");
        }
        render();
      });
    }
    render();
  }

  // ------------------------------------------------------------------ tela dividida (estilo Databricks)
  // Conteúdo à esquerda, JupyterLab completo à direita (árvore de arquivos, notebooks, Git).
  const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch { /* sem storage: só não lembra */ } };
  const lembrar = (k) => { try { return localStorage.getItem(k); } catch { return null; } };

  function telaDividida(n, dados, abrir) {
    const html = document.documentElement;
    const existente = document.querySelector(".rl-painel-nb");
    if (existente && !abrir) {
      existente.remove();
      html.classList.remove("rl-split");
      guardar("rl-split", "0");
      return;
    }
    if (existente) return;
    // Um workspace do JupyterLab por aula: cada uma guarda o próprio layout e abre com a árvore
    // de arquivos na pasta da aula (sem isso, o Jupyter restaura o último estado, na raiz)
    const url = comToken(`${dados?.servicos?.jupyter?.url ?? "http://localhost:8888"}` +
      `/lab/workspaces/aula-${pad(n)}/tree/estudos/aula-${pad(n)}/aula-${pad(n)}.ipynb`);
    html.style.setProperty("--rl-w", lembrar("rl-split-w") || "50vw");
    const quadro = el("iframe", { src: url, title: "JupyterLab", allow: "clipboard-read; clipboard-write" });
    const arrasto = el("div", { class: "rl-arrasto", title: "Arraste para redimensionar" });
    const fechar = el("button", { class: "rl-aba" }, "Fechar ✕");
    fechar.onclick = () => {
      telaDividida(n, dados);
      document.querySelectorAll(".rl-acoes .md-button--primary").forEach((b) => { b.textContent = "Estudar com notebook"; });
    };
    const painel = el("aside", { class: "rl-painel-nb" }, arrasto,
      el("div", { class: "rl-nb-barra" },
        el("strong", { class: "rl-nb-titulo", title: "Pastas, notebooks, .py, .md, .sql e Git ficam na barra lateral do JupyterLab" }, `estudos/aula-${pad(n)}/`),
                el("a", { class: "rl-aba", href: url, target: "_blank", rel: "noopener" }, "Nova aba"), fechar),
      quadro);
    arrasto.addEventListener("pointerdown", (ev) => {
      ev.preventDefault();
      quadro.style.pointerEvents = "none"; // o iframe "engoliria" o movimento do mouse
      const mover = (e) => {
        const largura = Math.min(Math.max(window.innerWidth - e.clientX, window.innerWidth * 0.25), window.innerWidth * 0.75);
        html.style.setProperty("--rl-w", `${Math.round(largura)}px`);
      };
      const soltar = () => {
        quadro.style.pointerEvents = "";
        guardar("rl-split-w", html.style.getPropertyValue("--rl-w"));
        window.removeEventListener("pointermove", mover);
        window.removeEventListener("pointerup", soltar);
      };
      window.addEventListener("pointermove", mover);
      window.addEventListener("pointerup", soltar);
    });
    document.body.append(painel);
    html.classList.add("rl-split");
    guardar("rl-split", "1");
  }

  // ------------------------------------------------------------------ trilha (início)
  function trilha(dados) {
    let concluidas = 0, passou = 0, declarados = 0;
    for (const span of document.querySelectorAll(".rl-trilha")) {
      const a = dados.aulas[span.dataset.aula];
      const total = +span.dataset.criterios || 0;
      const marcados = Object.keys(a.criterios).length;
      const s = situacao(a, total);
      concluidas += !!a.concluida_em;
      passou += a.checks.passou;
      declarados += a.checks.declarados;
      span.replaceChildren(
        el("span", { class: `rl-status rl-${s.cls}` }, s.txt),
        el("small", { class: "rl-dica" },
          ` checks ${a.checks.passou}/${a.checks.declarados}${total ? ` · critérios ${Math.min(marcados, total)}/${total}` : ""}`),
      );
    }
    const resumo = document.getElementById("rl-resumo");
    const n = Object.keys(dados.aulas).length;
    resumo?.replaceChildren(
      el("div", { class: "rl-resumo" },
        el("div", {}, el("strong", {}, `${concluidas}/${n}`), " aulas concluídas ", barra(concluidas, n)),
        el("div", {}, el("strong", {}, `${passou}/${declarados}`), " checks passando ", barra(passou, declarados))),
    );
  }

  // ------------------------------------------------------------------ ambiente
  const FERRAMENTAS = [
    { id: "jupyter", nome: "JupyterLab", caminho: (p) => (p ? `/lab/tree/${p}` : "/lab") },
    { id: "minio", nome: "MinIO", caminho: () => "/browser/rais" },
    { id: "sparkui", nome: "Spark UI", caminho: () => "/" },
  ];

  function ambiente(caixa, dados) {
    const [idHash, arq] = location.hash.slice(1).split("=");
    const quadro = el("iframe", { class: "rl-iframe", title: "ferramenta" });
    const abas = el("div", { class: "rl-abas" });
    const nova = el("a", { class: "md-button", target: "_blank", rel: "noopener" }, "Abrir em nova aba");
    const abrir = (f, caminho = "") => {
      const s = dados?.servicos?.[f.id];
      let url = (s?.url ?? "") + f.caminho(caminho);
      if (f.id === "jupyter") url = comToken(url);
      abas.querySelectorAll("button").forEach((b) => b.classList.toggle("rl-ativa", b.dataset.id === f.id));
      nova.href = url;
      if (s && !s.no_ar) {
        quadro.removeAttribute("src");
        quadro.srcdoc = `<p style="font:16px sans-serif;padding:2rem">${f.nome} não está respondendo.` +
          (f.id === "sparkui" ? " A Spark UI só existe enquanto uma sessão Spark está aberta." : " Rode <code>make up</code>.") + "</p>";
      } else {
        quadro.removeAttribute("srcdoc");
        quadro.src = url;
      }
      history.replaceState(null, "", `#${f.id}${caminho ? `=${encodeURIComponent(caminho)}` : ""}`);
    };
    for (const f of FERRAMENTAS) {
      const s = dados?.servicos?.[f.id];
      const b = el("button", { class: "rl-aba", "data-id": f.id },
        el("span", { class: `rl-ponto ${s?.no_ar ? "rl-on" : "rl-off"}` }), f.nome);
      b.onclick = () => abrir(f);
      abas.append(b);
    }
    abas.append(nova);
    caixa.replaceChildren(abas, quadro);
    abrir(FERRAMENTAS.find((f) => f.id === idHash) ?? FERRAMENTAS[0], arq ? decodeURIComponent(arq) : "");
  }

  // ------------------------------------------------------------------ preferências de leitura
  // Ao lado da pesquisa: tamanho da fonte e largura do conteúdo (o tema claro/escuro é o
  // botão nativo do Zensical, configurado em theme.palette no mkdocs.yml).
  function preferencias() {
    const html = document.documentElement;
    const aplicar = () => {
      html.style.setProperty("--rl-escala", lembrar("rl-escala") || "1");
      html.classList.toggle("rl-largo", lembrar("rl-largo") === "1");
    };
    aplicar();
    // Faixa logo abaixo do cabeçalho, acima do título, alinhada à direita
    const conteudo = document.querySelector(".md-content");
    if (!conteudo || document.querySelector(".rl-prefs")) return;
    const botao = (rotulo, titulo, acao) => {
      const b = el("button", { class: "rl-pref", title: titulo, "aria-label": titulo }, rotulo);
      b.onclick = () => { acao(); aplicar(); };
      return b;
    };
    const escala = (passo) => () => {
      const atual = parseFloat(lembrar("rl-escala") || "1");
      guardar("rl-escala", String(Math.min(1.6, Math.max(0.8, Math.round((atual + passo) * 10) / 10))));
    };
    const player = leitor();
    let abrirLeitor = null;
    if (player) {
      player.hidden = true;
      abrirLeitor = el("button", { class: "rl-pref", title: "Ouvir a página (leitura em voz alta)",
        "aria-label": "Ouvir a página" }, "🔊 Ouvir");
      abrirLeitor.onclick = () => { player.hidden = !player.hidden; };
    }
    conteudo.prepend(el("div", { class: "rl-prefs" }, abrirLeitor, player,
      botao("A−", "Diminuir a fonte", escala(-0.1)),
      botao("A", "Fonte padrão", () => guardar("rl-escala", "1")),
      botao("A+", "Aumentar a fonte", escala(0.1)),
      botao("↔", "Alternar largura do conteúdo", () => guardar("rl-largo", lembrar("rl-largo") === "1" ? "0" : "1")),
    ));
  }

  // ------------------------------------------------------------------ leitura em voz alta
  // Usa a síntese de voz do próprio navegador (Web Speech API): nada é enviado a servidor do
  // curso. Lê bloco a bloco (um texto longo de uma vez é cortado em alguns navegadores),
  // destaca o trecho atual e pula código e painéis.
  const BLOCOS = "h1, h2, h3, h4, p, li, td, th, .admonition-title, summary";
  const PULAR = "pre, code.rl-chip, .rl-aula, .rl-prefs, .rl-lateral, .rl-leitor, .md-source-file";

  function textoDoBloco(b) {
    const copia = b.cloneNode(true);
    copia.querySelectorAll(`.headerlink, pre, ${BLOCOS}`).forEach((x) => x.remove());
    return copia.textContent.replace(/\s+/g, " ").trim();
  }

  function blocosDaPagina() {
    const raizTexto = document.querySelector(".md-content__inner");
    if (!raizTexto) return [];
    return [...raizTexto.querySelectorAll(BLOCOS)]
      .filter((b) => !b.closest(PULAR))
      // li que só embrulha parágrafos: os parágrafos já são lidos
      .filter((b) => !(b.tagName === "LI" && b.querySelector(":scope > p")))
      .filter((b) => textoDoBloco(b));
  }

  function leitor() {
    const voz = window.speechSynthesis;
    if (!voz) return null;
    let fila = [], posicao = 0, ativo = false;
    const vozesPt = () => voz.getVoices().filter((v) => v.lang.toLowerCase().startsWith("pt"))
      // vozes neurais ("Natural"/"Online") primeiro, depois as de pt-BR
      .sort((a, b) => (/natural|online/i.test(b.name) - /natural|online/i.test(a.name))
        || (b.lang === "pt-BR") - (a.lang === "pt-BR"));
    const seletorVoz = el("select", { class: "rl-voz", title: "Voz" });
    const seletorVel = el("select", { class: "rl-vel", title: "Velocidade" },
      ...["0.75", "1", "1.25", "1.5", "1.75", "2"].map((v) => el("option", { value: v }, `${v.replace(".", ",")}×`)));
    seletorVel.value = lembrar("rl-voz-vel") || "1";
    seletorVel.onchange = () => guardar("rl-voz-vel", seletorVel.value);
    const preencherVozes = () => {
      const vozes = vozesPt();
      seletorVoz.replaceChildren(...vozes.map((v) =>
        el("option", { value: v.name }, v.name.replace(/^Microsoft /, "").replace(/ - .*$/, ""))));
      const salva = lembrar("rl-voz-nome");
      if (salva && vozes.some((v) => v.name === salva)) seletorVoz.value = salva;
    };
    preencherVozes();
    voz.onvoiceschanged = preencherVozes;
    seletorVoz.onchange = () => guardar("rl-voz-nome", seletorVoz.value);

    const tocar = el("button", { class: "rl-pref", title: "Ler / pausar" }, "▶");
    const parar = el("button", { class: "rl-pref", title: "Parar" }, "⏹");
    const marcar = (b) => {
      document.querySelectorAll(".rl-lendo").forEach((x) => x.classList.remove("rl-lendo"));
      if (b) { b.classList.add("rl-lendo"); b.scrollIntoView({ block: "center", behavior: "smooth" }); }
    };
    const encerrar = () => { ativo = false; voz.cancel(); marcar(null); tocar.textContent = "▶"; };
    const falar = () => {
      if (!ativo || posicao >= fila.length) return encerrar();
      const item = fila[posicao];
      const u = new SpeechSynthesisUtterance(item.texto);
      u.lang = "pt-BR";
      u.rate = parseFloat(seletorVel.value);
      u.voice = voz.getVoices().find((v) => v.name === seletorVoz.value) || null;
      u.onend = () => { posicao += 1; falar(); };
      u.onerror = (e) => { if (e.error !== "interrupted" && e.error !== "canceled") { posicao += 1; falar(); } };
      marcar(item.bloco);
      voz.speak(u);
    };
    tocar.onclick = () => {
      if (ativo && voz.speaking && !voz.paused) { voz.pause(); tocar.textContent = "▶"; return; }
      if (ativo && voz.paused) { voz.resume(); tocar.textContent = "⏸"; return; }
      const selecao = String(window.getSelection() || "").trim();
      if (selecao) {
        fila = [{ texto: selecao, bloco: null }];
      } else {
        const blocos = blocosDaPagina();
        // começa no primeiro bloco visível: role até onde parou e aperte play
        const inicio = Math.max(0, blocos.findIndex((b) => b.getBoundingClientRect().bottom > 80));
        fila = blocos.slice(inicio).map((b) => ({ texto: textoDoBloco(b), bloco: b }));
      }
      posicao = 0;
      ativo = true;
      voz.cancel();
      tocar.textContent = "⏸";
      falar();
    };
    parar.onclick = encerrar;
    window.addEventListener("pagehide", () => voz.cancel());
    return el("span", { class: "rl-leitor" }, tocar, parar, seletorVel, seletorVoz);
  }

  // ------------------------------------------------------------------ prévia das citações do guia
  // Clicar em "Parte 4.5" mostra o trecho do guia num cartão, sem sair do lugar da leitura.
  // A página do guia continua disponível pelo botão "Abrir no guia" (nova aba).
  const cacheGuia = new Map();

  async function trechoDoGuia(href) {
    const url = new URL(href, location.href);
    if (!cacheGuia.has(url.pathname)) {
      cacheGuia.set(url.pathname, fetch(url.pathname).then((r) => r.text())
        .then((html) => new DOMParser().parseFromString(html, "text/html")));
    }
    const doc = await cacheGuia.get(url.pathname);
    const artigo = doc.querySelector(".md-content__inner") || doc.body;
    const inicio = url.hash ? artigo.querySelector(url.hash) : artigo.querySelector("h1");
    if (!inicio) return null;
    // A seção vai do título até o próximo título do mesmo nível (ou superior)
    const nivel = Number(inicio.tagName[1]);
    const partes = [inicio.cloneNode(true)];
    for (let n = inicio.nextElementSibling; n; n = n.nextElementSibling) {
      if (/^H[1-6]$/.test(n.tagName) && Number(n.tagName[1]) <= nivel) break;
      partes.push(n.cloneNode(true));
    }
    partes.forEach((p) => p.querySelectorAll(".headerlink").forEach((x) => x.remove()));
    // Links relativos do guia passam a valer a partir da página da aula
    partes.forEach((p) => p.querySelectorAll("a[href]").forEach((a) => {
      a.setAttribute("href", new URL(a.getAttribute("href"), url).href);
    }));
    return partes;
  }

  function fecharPrevia() { document.querySelector(".rl-previa")?.remove(); }

  function previasDoGuia() {
    if (location.pathname.includes("/guia/")) return;    // nas páginas do guia, navega normal
    document.addEventListener("click", async (ev) => {
      const link = ev.target.closest(".md-content a[href*='guia/parte-'], .md-content a[href*='guia/apendice-']");
      if (!link || ev.ctrlKey || ev.metaKey || ev.shiftKey) return;   // Ctrl+clique: nova aba normal
      ev.preventDefault();
      fecharPrevia();
      const cartao = el("div", { class: "rl-previa md-typeset", role: "dialog", "aria-label": "Trecho do guia" });
      const fechar = el("button", { class: "rl-pref", title: "Fechar (Esc)" }, "✕");
      fechar.onclick = fecharPrevia;
      const corpo = el("div", { class: "rl-previa-corpo" }, el("p", { class: "rl-dica" }, "Carregando o trecho do guia…"));
      cartao.append(
        el("div", { class: "rl-previa-barra" },
          el("strong", {}, `Guia — ${link.textContent.trim()}`),
          el("a", { class: "md-button", href: link.href, target: "_blank", rel: "noopener" }, "Abrir no guia ↗"),
          fechar),
        corpo);
      document.body.append(cartao);
      const r = link.getBoundingClientRect();
      cartao.style.top = `${Math.min(r.bottom + 8, window.innerHeight - cartao.offsetHeight - 12)}px`;
      cartao.style.left = `${Math.max(12, Math.min(r.left, window.innerWidth - cartao.offsetWidth - 12))}px`;
      try {
        const partes = await trechoDoGuia(link.getAttribute("href"));
        corpo.replaceChildren(...(partes || [el("p", {}, "Trecho não encontrado; use Abrir no guia.")]));
      } catch {
        corpo.replaceChildren(el("p", {}, "Não consegui carregar o trecho; use Abrir no guia."));
      }
    });
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") fecharPrevia(); });
    document.addEventListener("click", (ev) => {
      const aberto = document.querySelector(".rl-previa");
      if (aberto && !aberto.contains(ev.target) && !ev.target.closest("a[href*='guia/']")) fecharPrevia();
    });
  }

  // ------------------------------------------------------------------ início
  document.addEventListener("DOMContentLoaded", async () => {
    preferencias();
    previasDoGuia();
    const painel = document.querySelector(".rl-aula");
    const amb = document.getElementById("rl-ambiente");
    if (!painel && !amb && !document.querySelector(".rl-trilha")) return;
    let dados = null;
    try { [dados] = await Promise.all([carregar(), iniciarSessao()]); }
    catch {
      const msg = "API de progresso fora do ar (porta 8001). Suba com: docker compose up -d curso";
      if (painel) aviso(painel, msg);
      const r = document.getElementById("rl-resumo");
      if (r) aviso(r, msg);
    }
    if (amb) ambiente(amb, dados);
    if (!dados) return;
    if (painel) {
      // Quem estava com a tela dividida continua com ela ao trocar de aula
      if (lembrar("rl-split") === "1") telaDividida(painel.dataset.aula, dados, true);
      paginaAula(painel, dados);
    }
    if (document.querySelector(".rl-trilha")) trilha(dados);
  });
})();
