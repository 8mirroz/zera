---
name: e-commerce
description: E-commerce patterns for Web and Mini Apps
---

# E-commerce Skill

## Overview
Patterns for building robust e-commerce flows (Catalog, Cart, Checkout).

## 1. Product Catalog
- **Grid Layout**: Responsive grid (2 cols mobile, 4 cols desktop).
- **Lazy Loading**: Use `IntersectionObserver` for images.
- **Filtering**: Client-side for <1000 items, Server-side for >1000.

## 2. Cart Management
- **Persistence**: `localStorage` + Sync with backend on init.
- **Optimistic UI**: Update UI immediately, then sync API.
- **Debounce**: Delay API calls for quantity updates (500ms).

```typescript
// Cart Store (Zustand)
interface CartState {
  items: CartItem[];
  addItem: (product: Product) => void;
  removeItem: (id: string) => void;
  total: number;
}
```

## 3. Checkout Flow
1. **Validation**: Check stock before payment.
2. **Payment**: Trigger Telegram Invoice or TON Transaction.
3. **Confirmation**: Show success screen + concise receipt.
4. **Haptics**: `notificationOccurred('success')` on purchase.

## 4. Post-Purchase
- **Order History**: Store locally and fetch recent.
- **Support**: Direct link to support bot/chat.
- **Retention**: Push notification permission request (optional).
