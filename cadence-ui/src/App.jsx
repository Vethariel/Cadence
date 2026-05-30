import { useCadenceStore } from './store'
import Chat from './components/Chat'
import Productions from './components/Productions'
import Player from './components/Player'
import Visualizer from './components/Visualizer'
import FrequencyAnalyzer from './components/FrequencyAnalyzer'
import LandingPage from './components/LandingPage'
import './index.css'

export default function App() {
  const rsong = useCadenceStore(s => s.rsong)
  const appScreen = useCadenceStore(s => s.appScreen)
  const enterStudio = useCadenceStore(s => s.enterStudio)
  const leftPaneView = useCadenceStore(s => s.leftPaneView)
  const setLeftPaneView = useCadenceStore(s => s.setLeftPaneView)

  if (appScreen === 'landing') {
    return <LandingPage onEnterStudio={enterStudio} />
  }

  return (
    <div className="app-shell">
      <aside className="left-pane">
        <div className="left-pane-tabs">
          <button
            type="button"
            className={`left-tab-btn ${leftPaneView === 'chat' ? 'active' : ''}`}
            onClick={() => setLeftPaneView('chat')}
          >
            Chat
          </button>
          <button
            type="button"
            className={`left-tab-btn ${leftPaneView === 'productions' ? 'active' : ''}`}
            onClick={() => setLeftPaneView('productions')}
          >
            Mis producciones
          </button>
        </div>
        <div className="panel panel-main-left">
          {leftPaneView === 'chat' ? <Chat /> : <Productions />}
        </div>
      </aside>

      <main className="right-pane">
        {rsong ? (
          <>
            <section className="right-stage">
              <Visualizer />
              <FrequencyAnalyzer />
            </section>
            <section className="right-player-dock">
              <Player />
            </section>
          </>
        ) : (
          <div className="empty-player-state">
            <div className="empty-player-title">Selecciona o genera una canción</div>
            <p>
              Tus producciones permanecen visibles mientras chateas y compones.
              Abre una para previsualizar, buscar, exportar RSong/MIDI e
              inspeccionar todos los metadatos técnicos.
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
