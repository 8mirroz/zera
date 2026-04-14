---
name: telegram-miniapp
description: Develop Telegram Mini Apps using React and native SDKs
---

# Telegram Mini Apps Skill

## Overview
Building premium Mini Apps that feel native to Telegram.

## Initialization (Critical)
```typescript
// App.tsx - MUST be first
import { useEffect } from 'react';

function App() {
  useEffect(() => {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
    window.Telegram.WebApp.enableClosingConfirmation();
  }, []);
  
  return <YourApp />;
}
```

## Native Components

### MainButton
```typescript
useEffect(() => {
  const webApp = window.Telegram.WebApp;
  webApp.MainButton.setText('Оформить заказ');
  webApp.MainButton.show();
  
  const handleClick = () => processCheckout();
  webApp.MainButton.onClick(handleClick);
  
  return () => {
    webApp.MainButton.offClick(handleClick);
    webApp.MainButton.hide();
  };
}, []);
```

### BackButton
```typescript
useEffect(() => {
  const webApp = window.Telegram.WebApp;
  webApp.BackButton.show();
  webApp.BackButton.onClick(() => navigate(-1));
  return () => webApp.BackButton.hide();
}, []);
```

### HapticFeedback
```typescript
// Success
window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');

// Selection
window.Telegram.WebApp.HapticFeedback.selectionChanged();
```

## Theme Sync
```css
:root {
  --bg: var(--tg-theme-bg-color, #ffffff);
  --text: var(--tg-theme-text-color, #000000);
  --button: var(--tg-theme-button-color, #3390ec);
}
```

## Performance Targets
- **API Latency:** < 100ms
- **UI Load:** < 2 seconds
- **Frame Rate:** 60 FPS

## Navigation v2 (Telegram SDK 7.0+)

### Menu Component
```typescript
// New native menu for complex navigation
useEffect(() => {
  const webApp = window.Telegram.WebApp;
  
  webApp.MainButton.setParams({
    text: 'Open Menu',
    is_visible: true
  });
  
  webApp.MainButton.onClick(() => {
    webApp.showPopup({
      title: 'Navigation',
      message: 'Choose a section',
      buttons: [
        { id: 'catalog', type: 'default', text: 'Catalog' },
        { id: 'cart', type: 'default', text: 'Cart' },
        { id: 'profile', type: 'default', text: 'Profile' }
      ]
    }, (buttonId) => {
      navigate(`/${buttonId}`);
    });
  });
}, []);
```

### Tabs Component
```typescript
// Bottom navigation tabs (native-like)
const tabs = [
  { id: 'home', icon: '🏠', label: 'Home' },
  { id: 'search', icon: '🔍', label: 'Search' },
  { id: 'cart', icon: '🛒', label: 'Cart' }
];

// Render as fixed bottom bar
<nav className="fixed bottom-0 w-full bg-[var(--tg-theme-bg-color)]">
  {tabs.map(tab => (
    <button 
      key={tab.id}
      onClick={() => {
        navigate(`/${tab.id}`);
        window.Telegram.WebApp.HapticFeedback.selectionChanged();
      }}
    >
      {tab.icon} {tab.label}
    </button>
  ))}
</nav>
```

## Resources
- [Telegram WebApp SDK](https://core.telegram.org/bots/webapps)
- [SDK 7.0 Release Notes](https://core.telegram.org/bots/webapps#v7-0)
