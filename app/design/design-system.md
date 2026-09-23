# Nebula Design System and Backend Coverage

## Coverage map

The dashboard and Telegram surface may only call capabilities that exist in this repository. `Implemented` means the service exists and has a real trigger/output. `Backend gap` means the requested capability is not currently implemented and therefore has no honest UI trigger yet.

| Domain | Backend capability | Current implementation | UI surface / trigger | Status |
|---|---|---|---|---|
| Inventory | `search_products` | `InventoryService.search_products` | Inventory search field and command desk product lookup | Implemented |
| Inventory | `get_product` | `get_product_by_id`, `get_product_by_sku` | Product search/detail data in the live Inventory workspace | Implemented |
| Inventory | `receive_stock` | `InventoryService.receive_stock` | Receive stock form and Telegram receive command | Implemented |
| Inventory | `check_stock` | `InventoryService.check_stock` | Stock detail panel and command desk | Implemented |
| Inventory | `get_low_stock_products` | `InventoryService.get_low_stock_products` | Low-stock data is included in `/api/dashboard/snapshot` for the live workspace | Implemented |
| Inventory | `adjust_stock` | `InventoryService.adjust_stock` | `/api/dashboard/inventory/adjust` adapter is available for the adjustment action | Implemented |
| Billing | `create_bill` | `BillingService.create_bill` | New bill action and billing workspace | Implemented |
| Billing | `add_item_to_bill` | `BillingService.add_item_to_bill` | Bill item composer | Implemented |
| Billing | `remove_item_from_bill` | `BillingService.remove_item_from_bill` | Service exists but no dashboard item-edit route yet | Backend adapter gap |
| Billing | `update_bill_item` | `BillingService.update_bill_item` | Service exists but no dashboard item-edit route yet | Backend adapter gap |
| Billing | `get_bill` | `BillingService.get_bill` | `/api/dashboard/bills/{id}` and Bills workspace | Implemented |
| Billing | `calculate_bill` | `BillingService.calculate_bill` | Bill detail response provides live totals | Implemented |
| Billing | `finalize_bill` | `BillingService.finalize_bill` | Finalize confirmation and invoice action | Implemented |
| Payments | `record_payment` | No payment service or function exists | No fabricated payment control; credit/payment is exposed only through existing khata flow | Backend gap |
| Khata | `find_customer` | `KhataService.find_customer` | Customer search and khata lookup | Implemented |
| Khata | `create_customer` | `KhataService.create_customer` | New customer form | Implemented |
| Khata | `add_credit` | `KhataService.add_credit` | Add credit transaction form | Implemented |
| Khata | `record_credit_payment` | `KhataService.record_credit_payment` | Record payment form | Implemented |
| Khata | `get_customer_balance` | `KhataService.get_customer_balance` | Customer balance card | Implemented |
| Analytics | `get_daily_sales` | No analytics service exists | No fake chart; analytics section reports backend gap | Backend gap |
| Analytics | `get_weekly_sales` | No analytics service exists | No fake chart; analytics section reports backend gap | Backend gap |
| Analytics | `get_monthly_sales` | No analytics service exists | No fake chart; analytics section reports backend gap | Backend gap |
| Analytics | `get_top_products` | No analytics service exists | No fake chart; analytics section reports backend gap | Backend gap |
| Analytics | `get_sales_by_payment_method` | No analytics service exists | No fake chart; analytics section reports backend gap | Backend gap |
| Analytics | `get_gst_summary` | No analytics service exists | GST dashboard tile is unavailable until a real endpoint exists | Backend gap |
| Analytics | `get_stock_health` | No analytics service exists | UI uses existing low-stock service only; health chart is marked unavailable | Backend gap |
| Analytics | `get_customer_credit_summary` | No analytics service exists | UI uses per-customer balance only; aggregate exposure is marked unavailable | Backend gap |
| Documents | `generate_invoice_pdf` | `InvoiceService.render_pdf` and `filename` | Invoice action opens PDF preview/download | Implemented |
| Documents | `generate_sales_deck` | No PPTX generator exists | No fake deck archive; document panel reports backend gap | Backend gap |
| Preferences | `get_preference` | `UserPreference` model only; no service/function | Settings panel reports persistence backend gap | Backend gap |
| Preferences | `set_preference` | `UserPreference` model only; no service/function | Settings panel reports persistence backend gap | Backend gap |
| Agent/System | conversation/session state | Models exist; no session API wired to web UI | No session browser is exposed; Telegram uses a stateless request wrapper | Backend adapter gap |
| Agent/System | idempotency records | Model exists; no generic idempotency service/API | Credit-bill idempotency is visible in operation result; record browser is unavailable | Partial |
| Agent/System | tool-call logs | No observability log model/service exists | Activity panel shows only real request results, not fabricated tool telemetry | Backend gap |
| Agent/System | `/health` | `GET /api/health` | System health widget | Implemented |

## Shared visual language

- Palette: deep navy, mineral teal, muted coral, amber semantic warning, and a neutral grey ramp.
- Typography: Newsreader for display moments, Manrope for product UI, DM Mono for IDs, SKU values, and monetary figures.
- Layout: 8px spacing scale with a 12-column desktop grid and 1-column mobile collapse.
- States: every request panel has idle, loading, success, and error rendering. Backend gaps are explicit product copy, never fake metrics.
- Motion: 180ms ease-out transitions for hover, drawer, and result state changes.
- Accessibility: visible focus rings, labelled controls, text plus color for statuses, and keyboard-submit support.

## Boundary notes

The current repository does not contain analytics, payments, PPTX, preference, or observability services. Building UI controls that imply those operations would violate the requirement to use existing backend behavior only. Those rows become available when the corresponding service and route are added.
