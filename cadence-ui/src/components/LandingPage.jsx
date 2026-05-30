import { useEffect, useRef } from 'react'

function ArchitectureGraph() {
  return (
    <div className="lp-graph">
      <svg viewBox="0 0 1280 420" className="lp-graph-lines" aria-hidden="true">
        <path d="M120 84 H320 M350 84 H560 M590 84 H790 M820 84 H1040" />
        <path d="M120 182 H320 M350 182 H560 M590 182 H790 M820 182 H1040" />
        <path d="M220 106 V160 M680 106 V160" />
        <path d="M1035 204 C1120 204 1120 312 920 312 H220 C95 312 70 230 120 182" />
      </svg>
      <div className="lp-graph-node a">Prompt</div>
      <div className="lp-graph-node b">LLM Brief</div>
      <div className="lp-graph-node c">LLM Técnico</div>
      <div className="lp-graph-node d">Prepare + Seeds</div>
      <div className="lp-graph-node e">Narrativa/Estructura</div>
      <div className="lp-graph-node f">Policy + Strategy</div>
      <div className="lp-graph-node g">Harmony + Development</div>
      <div className="lp-graph-node h">Orquestación</div>
      <div className="lp-graph-node i">Composición</div>
      <div className="lp-graph-node j">Post Process</div>
      <div className="lp-graph-node k">Validator</div>
      <div className="lp-graph-node l">Repair Loop</div>
      <div className="lp-graph-node m">Export RSong/MIDI</div>
    </div>
  )
}

function WaveCard() {
  return (
    <div className="lp-wave-card">
      <div className="lp-wave-title">Engine de respuesta musical</div>
      <div className="lp-bars">
        {Array.from({ length: 28 }).map((_, i) => (
          <span key={i} style={{ animationDelay: `${i * 0.05}s` }} />
        ))}
      </div>
      <p>Respuesta en tiempo real para BPM, densidad, capas y exportación reproducible.</p>
    </div>
  )
}

export default function LandingPage({ onEnterStudio }) {
  const shellRef = useRef(null)

  useEffect(() => {
    const shell = shellRef.current
    if (!shell) return
    const resetScroll = () => {
      shell.scrollTop = 0
      shell.scrollLeft = 0
    }
    resetScroll()
    requestAnimationFrame(resetScroll)
  }, [])

  return (
    <div ref={shellRef} className="landing-shell lp-shell">
      <div className="landing-header lp-header">
        <span>CADENCE // Plataforma de composición musical agentic</span>
        <button type="button" onClick={onEnterStudio} className="landing-enter-btn">
          Entrar al Studio
        </button>
      </div>

      <div className="landing-slides lp-slides">
        <section className="landing-slide lp-slide lp-hero">
          <div className="slide-index">01</div>
          <h1>Cadence compone música jugable, no solo demos.</h1>
          <h2>De una idea textual a una producción validada para gameplay.</h2>
          <p>
            La mayoría de herramientas generan clips. Cadence genera una pieza completa
            con estructura, narrativa, armonía y validación perceptual/técnica antes de exportar.
          </p>
          <div className="lp-hero-kpis">
            <div><strong>2</strong><span>nodos LLM especializados</span></div>
            <div><strong>16+</strong><span>nodos deterministas de control musical</span></div>
            <div><strong>Repair</strong><span>corrección automática por fallos específicos</span></div>
          </div>
          <button type="button" onClick={onEnterStudio} className="slide-cta">
            Comenzar ahora
          </button>
        </section>

        <section className="landing-slide lp-slide lp-graph-slide">
          <div className="slide-index">02</div>
          <h1>Arquitectura de Cadence</h1>
          <h2>Creatividad guiada por LLM + ejecución determinista trazable.</h2>
          <ArchitectureGraph />
        </section>

        <section className="landing-slide lp-slide lp-story">
          <div className="slide-index">03</div>
          <h1>¿Por qué suena mejor?</h1>
          <h2>Porque las decisiones críticas están separadas por responsabilidad.</h2>
          <div className="lp-grid-2">
            <div className="lp-card">
              <h3>Fase creativa</h3>
              <p>
                `prompt_enhancer` y `technical_spec` definen intención, arquetipo, textura y
                reglas de composición sin improvisar fuera del brief.
              </p>
            </div>
            <div className="lp-card">
              <h3>Fase de ingeniería musical</h3>
              <p>
                Nodos de estructura, armonía, desarrollo, arreglo, validación y repair
                convierten esas decisiones en una pieza consistente.
              </p>
            </div>
          </div>
          <WaveCard />
        </section>

        <section className="landing-slide lp-slide lp-io">
          <div className="slide-index">04</div>
          <h1>Input simple, output profundo.</h1>
          <h2>Un prompt entra. Sale RSong completo, auditable y reproducible.</h2>
          <div className="lp-grid-2">
            <div className="lp-card">
              <h3>Entrada</h3>
              <p>Un prompt por `POST /generate` con tu intención musical.</p>
              <p>Cadence infiere contexto narrativo, uso, energía y dirección de estilo.</p>
            </div>
            <div className="lp-card">
              <h3>Salida</h3>
              <p>
                `.rsong` con `header`, `game_meta`, `harmony`, `development`,
                `arrangement`, `validation`, `quality`, y trazabilidad del pipeline.
              </p>
            </div>
          </div>
        </section>

        <section className="landing-slide lp-slide lp-close">
          <div className="slide-index">05</div>
          <h1>Cadence convierte prompts en assets musicales listos para iterar.</h1>
          <h2>Menos incertidumbre creativa. Más control, más velocidad, más calidad.</h2>
          <p>
            Si necesitas música de juego consistente, explicable y exportable, Cadence te da
            el balance entre dirección artística y rigor técnico.
          </p>
          <button type="button" onClick={onEnterStudio} className="slide-cta">
            Entrar al Studio
          </button>
        </section>
      </div>
    </div>
  )
}
