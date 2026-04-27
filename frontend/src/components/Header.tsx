import './Header.css'

export function Header() {
  return (
    <header className="header">
      <div className="header-content">
        <div className="logo">
          <span className="logo-icon">🌌</span>
          <div className="logo-text">
            <h1>Dune Bot</h1>
            <span className="subtitle">Arrakis Dominion</span>
          </div>
        </div>
      </div>
    </header>
  )
}