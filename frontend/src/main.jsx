import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import PageApp from './PageApp'
import styles from './styles/index.css?inline'

function injectStyles(shadowRoot) {
  if (styles) {
    const styleEl = document.createElement('style')
    styleEl.textContent = styles
    shadowRoot.appendChild(styleEl)
  }
}

function initPageMode(mount) {
  const host = document.createElement('div')
  host.id = 'e2next-ai-page-host'
  host.style.cssText = 'height: 100%; width: 100%;'
  mount.appendChild(host)

  const shadowRoot = host.attachShadow({ mode: 'open' })
  injectStyles(shadowRoot)

  const mountEl = document.createElement('div')
  mountEl.id = 'e2next-ai-page-root'
  mountEl.style.cssText = 'height: 100%; width: 100%;'
  shadowRoot.appendChild(mountEl)

  ReactDOM.createRoot(mountEl).render(
    React.createElement(PageApp)
  )
}

function initWidgetMode() {
  if (document.getElementById('e2next-ai-host')) return

  const host = document.createElement('div')
  host.id = 'e2next-ai-host'
  document.body.appendChild(host)

  const shadowRoot = host.attachShadow({ mode: 'open' })
  injectStyles(shadowRoot)

  const mountEl = document.createElement('div')
  mountEl.id = 'e2next-ai-root'
  shadowRoot.appendChild(mountEl)

  ReactDOM.createRoot(mountEl).render(
    React.createElement(App)
  )
}

function initChatbot() {
  const pageMount = document.getElementById('e2next-ai-page-mount')
  if (pageMount) {
    initPageMode(pageMount)
  } else {
    initWidgetMode()
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initChatbot)
} else {
  initChatbot()
}
