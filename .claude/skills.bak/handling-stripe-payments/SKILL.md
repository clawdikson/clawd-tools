---
name: handling-stripe-payments
description: Implement Stripe payment flows including payment intents, validation, webhooks, and error handling. Covers the payment validation lifecycle between Frontend, Backend, and Native App. Use when working with payments, checkout, billing, or payment_intent_id validation.
---

# Handling Stripe Payments

Implement and debug Stripe payment flows in the Beena Automation Platform. This skill covers payment intent creation, validation between services, webhook handling, and common payment patterns.

## When to Use This Skill

- Creating new payment flows or checkout experiences
- Implementing payment validation in Native App
- Debugging payment failures or webhook issues
- Adding new Stripe features (subscriptions, refunds)
- Understanding the payment_intent_id validation flow

## Payment Architecture Overview

### Project Structure

```
Frontend (automation-webapp-fe)
├── src/
│   ├── components/checkout/
│   │   └── StripeCheckout.tsx       # Stripe Elements integration
│   └── services/
│       └── paymentService.ts         # Payment API calls

Backend (automation-webapp-be)
├── src/
│   ├── application/useCases/
│   │   └── payments/
│   │       ├── createPaymentIntent.js   # Create payment intent
│   │       └── validatePayment.js       # Validate payment status
│   ├── interfaces/http/
│   │   ├── controllers/
│   │   │   └── paymentController.js     # HTTP handlers
│   │   └── routes/
│   │       └── payments.js              # Route definitions
│   └── infrastructure/
│       └── stripe/
│           └── stripeClient.js          # Stripe SDK wrapper

Native App (beena-native-app)
├── beenanativeapp/src/beenanativeapp/
│   └── services/
│       └── payment_validation.py        # Validates before migration
```

### Payment Flow Diagram

```
Frontend                    Backend                     Native App
   |                           |                              |
   |--1. Create Intent-------->|                              |
   |                           |--2. Stripe API: Create------>|
   |<--3. client_secret--------|                     (Stripe) |
   |                           |                              |
   |--4. User pays (Elements)->|                              |
   |                           |                    (Stripe)  |
   |<--5. Payment confirmed----|                              |
   |                           |                              |
   |--6. Start migration-------|-------------------------->|
   |                           |                              |
   |                           |<--7. Validate payment_intent-|
   |                           |--8. Check with Stripe------->|
   |                           |<--9. Payment status----------|
   |                           |--10. Validation result------>|
   |                           |                              |
   |                           |          (If valid, proceed) |
   |                           |<--11. Migration results------|
   |<--12. Status updates------|                              |
```

## Step 1: Environment Configuration

### Backend (.env)

```bash
# Stripe API Keys
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxx

# Payment validation cache (seconds)
PAYMENT_CACHE_TTL=1800 # 30 minutes
```

### Frontend (.env)

```bash
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxx
```

### Native App (.env)

```bash
BACKEND_API_URL=http://localhost:5001
PAYMENT_VALIDATION_ENABLED=true
```

## Step 2: Creating Payment Intents

### Backend Use Case

**src/application/useCases/payments/createPaymentIntent.js**:

```javascript
const stripe = require("../../../infrastructure/stripe/stripeClient");

module.exports = async function createPaymentIntent({
  amount,
  currency = "usd",
  userId,
  metadata = {},
}) {
  // Validate amount
  if (!amount || amount < 50) {
    throw new Error("Amount must be at least $0.50");
  }

  // Create payment intent with Stripe
  const paymentIntent = await stripe.paymentIntents.create({
    amount: Math.round(amount), // Stripe expects cents
    currency,
    metadata: {
      userId: userId.toString(),
      ...metadata,
    },
    automatic_payment_methods: {
      enabled: true,
    },
  });

  return {
    clientSecret: paymentIntent.client_secret,
    paymentIntentId: paymentIntent.id,
    amount: paymentIntent.amount,
    status: paymentIntent.status,
  };
};
```

### Backend Controller

**src/interfaces/http/controllers/paymentController.js**:

```javascript
const createPaymentIntent = require("../../../application/useCases/payments/createPaymentIntent");
const validatePayment = require("../../../application/useCases/payments/validatePayment");

exports.createPaymentIntent = async (req, res, next) => {
  try {
    const { amount, currency, metadata } = req.body;
    const userId = req.user.id;

    const result = await createPaymentIntent({
      amount,
      currency,
      userId,
      metadata,
    });

    res.json({
      success: true,
      data: result,
    });
  } catch (error) {
    next(error);
  }
};

exports.validatePayment = async (req, res, next) => {
  try {
    const { payment_intent_id } = req.body;

    const result = await validatePayment({
      paymentIntentId: payment_intent_id,
    });

    res.json({
      success: true,
      data: result,
    });
  } catch (error) {
    next(error);
  }
};
```

## Step 3: Payment Validation (Native App → Backend)

### Backend Validation Use Case

**src/application/useCases/payments/validatePayment.js**:

```javascript
const stripe = require("../../../infrastructure/stripe/stripeClient");
const NodeCache = require("node-cache");

// Cache validation results for 30 minutes
const paymentCache = new NodeCache({ stdTTL: 1800 });

module.exports = async function validatePayment({ paymentIntentId }) {
  if (!paymentIntentId) {
    throw new Error("Payment intent ID is required");
  }

  // Check cache first
  const cached = paymentCache.get(paymentIntentId);
  if (cached) {
    return cached;
  }

  // Fetch from Stripe
  const paymentIntent = await stripe.paymentIntents.retrieve(paymentIntentId);

  const result = {
    valid: paymentIntent.status === "succeeded",
    status: paymentIntent.status,
    amount: paymentIntent.amount,
    currency: paymentIntent.currency,
    metadata: paymentIntent.metadata,
    created: new Date(paymentIntent.created * 1000),
  };

  // Cache successful validations
  if (result.valid) {
    paymentCache.set(paymentIntentId, result);
  }

  return result;
};
```

### Native App Validation Service

**beenanativeapp/src/beenanativeapp/services/payment_validation.py**:

```python
import httpx
from functools import lru_cache
from datetime import datetime, timedelta
from typing import Optional
import os

class PaymentValidationError(Exception):
    """Raised when payment validation fails."""
    pass

class PaymentValidator:
    """Validates payment intents with the backend."""

    def __init__(self):
        self.backend_url = os.getenv('BACKEND_API_URL', 'http://localhost:5001')
        self.enabled = os.getenv('PAYMENT_VALIDATION_ENABLED', 'true').lower() == 'true'
        self._cache: dict = {}
        self._cache_ttl = timedelta(minutes=30)

    def _is_cached(self, payment_intent_id: str) -> Optional[dict]:
        """Check if validation result is cached and not expired."""
        if payment_intent_id in self._cache:
            cached = self._cache[payment_intent_id]
            if datetime.now() - cached['timestamp'] < self._cache_ttl:
                return cached['result']
        return None

    async def validate(self, payment_intent_id: str) -> dict:
        """
        Validate a payment intent with the backend.

        Args:
            payment_intent_id: The Stripe payment intent ID (pi_xxx)

        Returns:
            dict with 'valid', 'status', 'amount', 'metadata'

        Raises:
            PaymentValidationError: If validation fails or payment not succeeded
        """
        if not self.enabled:
            return {'valid': True, 'status': 'bypassed', 'message': 'Validation disabled'}

        if not payment_intent_id:
            raise PaymentValidationError('Payment intent ID is required')

        # Check cache
        cached = self._is_cached(payment_intent_id)
        if cached:
            return cached

        # Call backend validation endpoint
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f'{self.backend_url}/api/v1/payments/validate',
                    json={'payment_intent_id': payment_intent_id},
                    timeout=10.0,
                )

                if response.status_code != 200:
                    raise PaymentValidationError(
                        f'Backend validation failed: {response.status_code}'
                    )

                data = response.json()

                if not data.get('success'):
                    raise PaymentValidationError(
                        data.get('error', 'Validation failed')
                    )

                result = data['data']

                # Cache successful validations
                if result.get('valid'):
                    self._cache[payment_intent_id] = {
                        'result': result,
                        'timestamp': datetime.now(),
                    }

                return result

            except httpx.RequestError as e:
                raise PaymentValidationError(f'Network error: {str(e)}')

    def clear_cache(self):
        """Clear the validation cache."""
        self._cache.clear()


# Global validator instance
payment_validator = PaymentValidator()


async def validate_payment_before_migration(payment_intent_id: str) -> bool:
    """
    Validate payment before starting a migration.

    Returns True if payment is valid, raises exception otherwise.
    """
    result = await payment_validator.validate(payment_intent_id)

    if not result.get('valid'):
        raise PaymentValidationError(
            f"Payment not valid. Status: {result.get('status')}"
        )

    return True
```

### Using Validation in Automation Endpoint

**beenanativeapp/src/beenanativeapp/api/endpoints/automation.py**:

```python
from fastapi import APIRouter, HTTPException
from ...services.payment_validation import (
    validate_payment_before_migration,
    PaymentValidationError,
)

router = APIRouter()

@router.post("/run")
async def run_automation(request: AutomationRequest):
    """Execute automation with payment validation."""

    # Step 1: Validate payment
    try:
        await validate_payment_before_migration(request.payment_intent_id)
    except PaymentValidationError as e:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail=str(e),
        )

    # Step 2: Queue the automation job
    job_id = await job_manager.queue_job(request)

    return {"job_id": job_id, "status": "queued"}
```

## Step 4: Webhook Handling

### Backend Webhook Controller

**src/interfaces/http/controllers/webhookController.js**:

```javascript
const stripe = require("../../../infrastructure/stripe/stripeClient");
const config = require("../../../infrastructure/config");
const logger = require("../../../infrastructure/logging/logger");

exports.handleStripeWebhook = async (req, res) => {
  const sig = req.headers["stripe-signature"];
  let event;

  try {
    // Verify webhook signature
    event = stripe.webhooks.constructEvent(
      req.rawBody, // Must use raw body for signature verification
      sig,
      config.stripe.webhookSecret,
    );
  } catch (err) {
    logger.error("Webhook signature verification failed:", err.message);
    return res.status(400).send(`Webhook Error: ${err.message}`);
  }

  // Handle specific events
  switch (event.type) {
    case "payment_intent.succeeded":
      await handlePaymentSuccess(event.data.object);
      break;

    case "payment_intent.payment_failed":
      await handlePaymentFailure(event.data.object);
      break;

    case "charge.refunded":
      await handleRefund(event.data.object);
      break;

    default:
      logger.info(`Unhandled event type: ${event.type}`);
  }

  res.json({ received: true });
};

async function handlePaymentSuccess(paymentIntent) {
  logger.info(`Payment succeeded: ${paymentIntent.id}`);
  // Update workflow status, send confirmation email, etc.
}

async function handlePaymentFailure(paymentIntent) {
  logger.error(`Payment failed: ${paymentIntent.id}`, {
    error: paymentIntent.last_payment_error,
  });
  // Notify user, update status, etc.
}

async function handleRefund(charge) {
  logger.info(`Refund processed: ${charge.id}`);
  // Revoke access, update records, etc.
}
```

### Raw Body Middleware for Webhooks

**src/interfaces/http/middlewares/rawBody.js**:

```javascript
const express = require("express");

// This must be applied BEFORE express.json() for webhook routes
module.exports = function rawBodyMiddleware(req, res, next) {
  if (req.originalUrl === "/api/v1/webhooks/stripe") {
    let data = "";
    req.setEncoding("utf8");

    req.on("data", (chunk) => {
      data += chunk;
    });

    req.on("end", () => {
      req.rawBody = data;
      next();
    });
  } else {
    next();
  }
};
```

## Step 5: Frontend Integration

### Stripe Elements Component

**src/components/checkout/StripeCheckout.tsx**:

```typescript
import { useState } from 'react';
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);

interface CheckoutFormProps {
  clientSecret: string;
  onSuccess: (paymentIntentId: string) => void;
  onError: (error: string) => void;
}

function CheckoutForm({ clientSecret, onSuccess, onError }: CheckoutFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    setIsProcessing(true);

    const { error, paymentIntent } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: window.location.origin + '/payment/complete',
      },
      redirect: 'if_required',
    });

    if (error) {
      onError(error.message || 'Payment failed');
      setIsProcessing(false);
    } else if (paymentIntent && paymentIntent.status === 'succeeded') {
      onSuccess(paymentIntent.id);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <PaymentElement />
      <button type="submit" disabled={!stripe || isProcessing}>
        {isProcessing ? 'Processing...' : 'Pay Now'}
      </button>
    </form>
  );
}

export function StripeCheckout({
  clientSecret,
  onSuccess,
  onError,
}: CheckoutFormProps) {
  return (
    <Elements stripe={stripePromise} options={{ clientSecret }}>
      <CheckoutForm
        clientSecret={clientSecret}
        onSuccess={onSuccess}
        onError={onError}
      />
    </Elements>
  );
}
```

## Common Payment Error Codes

| Error Code                              | Meaning                   | Resolution                     |
| --------------------------------------- | ------------------------- | ------------------------------ |
| `card_declined`                         | Card was declined         | Ask user to try different card |
| `expired_card`                          | Card has expired          | Request updated card           |
| `incorrect_cvc`                         | CVC check failed          | Verify CVC entered correctly   |
| `processing_error`                      | Temporary Stripe issue    | Retry after a moment           |
| `insufficient_funds`                    | Insufficient funds        | Use different payment method   |
| `payment_intent_authentication_failure` | 3DS authentication failed | Retry authentication           |

## Testing Payments

### Test Card Numbers

```
# Success
4242424242424242    # Visa - succeeds
4000000000000077    # Visa - succeeds (no 3DS)

# Failures
4000000000000002    # Card declined
4000000000009995    # Insufficient funds
4000000000000069    # Expired card

# 3D Secure
4000002500003155    # Requires authentication
4000008400001629    # Authentication fails
```

### Test Webhook Events

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login and forward webhooks
stripe login
stripe listen --forward-to localhost:5001/api/v1/webhooks/stripe

# Trigger test events
stripe trigger payment_intent.succeeded
stripe trigger payment_intent.payment_failed
```

## Best Practices

1. **Always validate payment_intent_id** before starting migrations
2. **Cache validation results** (30 minutes) to reduce Stripe API calls
3. **Use webhooks** for reliable payment status updates
4. **Store raw request body** for webhook signature verification
5. **Never log full payment details** (use payment_intent_id only)
6. **Implement idempotency** for payment operations
7. **Handle edge cases**: expired intents, refunds, disputes
8. **Test with Stripe CLI** before deploying
9. **Use test mode keys** in development
10. **Monitor webhook failures** in Stripe dashboard
