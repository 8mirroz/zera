---
name: telegram-payments
description: Integration patterns for Telegram Stars and TON Connect
---

# Payment Integration Skill

## Overview
Integration patterns for digital (Stars) and crypto (TON) payments.

## 1. Telegram Stars (Digital Goods)
```python
from aiogram.types import LabeledPrice

@router.message(F.text == "/buy_premium")
async def send_invoice(message: Message, bot: Bot):
    prices = [LabeledPrice(label="Premium 1 месяц", amount=100)]
    
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Premium подписка",
        description="Доступ ко всем функциям",
        payload="premium_1month",
        provider_token="",  # Empty for Stars
        currency="XTR",     # Telegram Stars
        prices=prices
    )

@router.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)
```

## 2. TON Connect (Web3)
```typescript
import { TonConnectButton, useTonWallet } from '@tonconnect/ui-react';

function PaymentPage() {
  const wallet = useTonWallet();
  
  const sendPayment = async () => {
    if (!wallet) return;
    
    await wallet.sendTransaction({
      validUntil: Math.floor(Date.now() / 1000) + 360,
      messages: [{
        address: MERCHANT_WALLET,
        amount: '1000000000', // 1 TON in nanotons
      }]
    });
  };
  
  return (
    <>
      <TonConnectButton />
      {wallet && <button onClick={sendPayment}>Pay 1 TON</button>}
    </>
  );
}
```

## Security Checklist
- ✅ Validate `pre_checkout_query` on server
- ✅ Use webhooks for payment confirmation
- ✅ Verify TON transactions on-chain
- ✅ Store payment records in database
- ✅ Implement idempotency keys

## 💎 Advanced TON Ecosystem (Web3+)
**Pattern:** Beyond simple payments (Jettons, NFTs, Fragment)

### 1. Jetton Payments (Custom Tokens)
```typescript
// Pay using custom tokens (e.g., USDT on TON)
const jettonWalletAddress = await getJettonWallet(userAddress, USDT_MASTER);
await tonConnect.sendTransaction({
  messages: [{
    address: jettonWalletAddress,
    amount: toNano('5.0'), // 5 USDT
    payload: beginCell().storeUint(0x0f8a7ea5, 32).endCell() // op::transfer
  }]
});
```

### 2. Dynamic NFT Receipts
```python
# Mint NFT receipt upon successful purchase
async def mint_receipt_nft(user_address: str, order_id: str):
    metadata = {
        "name": f"Receipt #{order_id}",
        "image": f"https://api.myapp.com/receipts/{order_id}.png",
        "attributes": [{"trait_type": "Amount", "value": 100}]
    }
    # Call TON SDK to mint NFT
    return await ton_sdk.mint_item(collection_address, user_address, metadata)
```

## Resources
- [Telegram Payments](https://core.telegram.org/bots/payments)
- [TON Connect](https://docs.ton.org/develop/dapps/ton-connect/overview)
- [TON Jettons Docs](https://docs.ton.org/develop/smart-contracts/token-standards/jetton)
