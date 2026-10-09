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

    const render = () => {
      const marcados = caixas.filter((c) => c.checked).length;
      const s = situacao(atual, caixas.length);
      const itens = Object.entries(atual.checks.itens).map(([id, st]) =>
        el("code", { class: `rl-chip rl-${st}`, title: st }, `${st === "passou" ? "✓" : st === "falhou" ? "✗" : "–"} ${id}`));
      const botao = el("button", { class: "md-button rl-concluir" },
        atual.concluida_em ? "Desmarcar conclusão" : "Marcar aula como concluída");
      botao.onclick = async () => {
        botao.disabled = true;
        try { Object.assign(atual, await gravar({ aula: +n, concluida: !atual.concluida_em })); }
        catch { alert("Não consegui gravar: a API de progresso está no ar?"); }
        render();
      };
      const dividir = el("button", { class: "md-button md-button--primary" },
        document.documentElement.classList.contains("rl-split") ? "Fechar notebook" : "Estudar com notebook (tela dividida)");
      dividir.onclick = () => { telaDividida(n, dados); render(); };
      const acoes = [dividir, botao];
      if (painel.dataset.onde === "container") {
        const alvo = painel.dataset.lab ? `#jupyter=${encodeURIComponent(painel.dataset.lab)}` : "#jupyter";
        acoes.push(el("a", { class: "md-button", href: `${raiz}ambiente.html${alvo}` }, "Abrir arquivo da aula"));
      } else {
        acoes.push(el("span", { class: "rl-dica" }, `Checks no host: make check-host AULA=${pad(n)}`));
      }
      painel.replaceChildren(...[
        el("div", { class: "rl-cab" },
          el("span", { class: `rl-status rl-${s.cls}` }, s.txt),
          atual.concluida_em ? el("span", { class: "rl-dica" }, `em ${quando(atual.concluida_em)}`) : null),
        el("div", { class: "rl-linha" }, el("strong", {}, "Checks: "), textoChecks(atual.checks)),
        itens.length ? el("div", { class: "rl-chips" }, ...itens) : null,
        caixas.length ? el("div", { class: "rl-linha" }, el("strong", {}, "Critérios: "),
          `${marcados}/${caixas.length} marcados `, barra(marcados, caixas.length)) : null,
        el("div", { class: "rl-acoes" }, ...acoes),
      ].filter(Boolean));
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
    const url = comToken(`${dados?.servicos?.jupyter?.url ?? "http://localhost:8888"}/lab/tree/estudos/aula-${pad(n)}/aula-${pad(n)}.ipynb`);
    html.style.setProperty("--rl-w", lembrar("rl-split-w") || "50vw");
    const quadro = el("iframe", { src: url, title: "JupyterLab", allow: "clipboard-read; clipboard-write" });
    const arrasto = el("div", { class: "rl-arrasto", title: "Arraste para redimensionar" });
    const fechar = el("button", { class: "rl-aba" }, "Fechar ✕");
    fechar.onclick = () => { telaDividida(n, dados); document.querySelector(".rl-aula .md-button--primary").textContent = "Estudar com notebook (tela dividida)"; };
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

  // ------------------------------------------------------------------ início
  document.addEventListener("DOMContentLoaded", async () => {
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
