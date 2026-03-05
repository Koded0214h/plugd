# PlugD Backend


Document Title: Project Plug'd 2.0 - Complete Platform Rebuild

Version: 2.0
Date: February 16, 2026
Status: ---

 
Table of Contents

1. Executive Summary
2. Project Goals & Objectives
3. Scope of Work
o 3.1 In Scope (Core Features)
o 3.2 MVP Scope (Phase 1 Launch)
o 3.3 Out of Scope (Future Phases)
4. User Roles & Core Workflows
o 4.1 The Customer Journey
o 4.2 The Service Provider Journey
o 4.3 The Hub Journey (Agency/Coordinator)
o 4.4 The Admin Journey
5. Platform Architecture & Technology Stack
o 5.1 Frontend
o 5.2 Backend & Database
o 5.3 Payments
o 5.4 Media Management
o 5.5 Email & Communications
o 5.6 Architecture Diagram
6. UI/UX Design Integration
7. Feature Deep Dive
o 7.1 Request & Quote System
o 7.2 Booking & Calendar Engine
o 7.3 Admin Dashboard & Queues
o 7.4 Coupon & Discount System
o 7.5 Payout & Financials Hub
8. Testing Strategy
9. Project Timeline, Milestones & Deliverables (3 Months)
o 9.1 Month 1: Foundation
o 9.2 Month 2: Core Marketplace
o 9.3 Month 3: MVP Completion & Launch
10. Success Metrics (KPIs)
 
1. Executive Summary

Project Plug'd 2.0 is a complete strategic rebuild of the existing service marketplace. Moving beyond the limitations of version 1.0—which suffered from poor usability, manual workflows, and scalability constraints—this new platform is engineered to be intuitive, automated, and trustworthy.

Plug'd 2.0 will connect Customers, Service Providers, and Hubs (Agencies) in a structured ecosystem. By implementing clear roles, account-level verification, a flexible booking engine, and automated financial flows, the platform replaces the chaos of Instagram DMs and word-of-mouth with a reliable digital marketplace. This document outlines the complete scope, architecture, and 3-month development plan for delivering a high-quality Minimum Viable Product (MVP).

2. Project Goals & Objectives

• Solve Usability: Eliminate user confusion and drop-off during sign-up, service listing, and booking.
• Build Trust: Implement one-time, account-level verification and transaction-based performance tracking.
• Streamline Operations: Reduce manual admin workload by 80% through automation of verifications, notifications, and payouts.
• Enable Scalability: Build on a modern stack (React/Supabase) for rapid feature development without technical debt.
• Clarify Financials: Provide transparent payout calculations, real-time status updates, and self-service discount tools for providers.
3. Scope of Work

3.1 In Scope (Core Features)

• User System: Sign-up/Login for Customers, Providers, and Hubs. One-time ID verification tied to the account.
• Service Management: Direct service listings with visual calendars and a structured "Service Request" system.
• Booking & Payments: Visual calendar booking, Stripe Connect integration, secure payment holding, and automated provider payouts.
• Communication: Centralized in-app chat for negotiations, quotes, and project updates.
• Hub Functionality (Core): Ability for Hubs to create and manage multi-provider projects.
• Admin Panel: Role-based dashboard with queues for verifications, payouts, and platform settings.
3.2 MVP Scope (End of Month 3)

• Includes: All features in Section 3.1, with a focus on perfecting the core loops for Customers (find, book, pay) and Providers (get verified, list, get paid). Basic Hub accounts are included; advanced multi-provider coordination may be post-MVP.
• Goal: A fully functional, stable, and polished product ready for initial users.
3.3 Out of Scope (Post-MVP)

• Native mobile apps.
• Advanced analytics dashboards.
• Public API for third parties.
• Automated dispute resolution (admin-managed in MVP).
4. User Roles & Core Workflows

4.1 The Customer Journey

1. Discovery: Browse services by category. View verified provider profiles with portfolios and reviews. Check availability on a visual calendar.
2. Booking or Requesting:
o Direct Booking: Select an available slot and click "Book Now." The slot is instantly locked.
o Service Request: Post a detailed request. Receive and compare quotes from providers via in-app chat.
3. Checkout: Receive an actionable email with a "Complete Payment" link. Pay securely via Stripe.
4. Post-Service: Confirm completion, leave a review, and easily re-book.
4.2 The Service Provider Journey

1. Onboarding & Verification: Sign up, select "Provider," upload ID once. Status is tracked in dashboard. (Solves repeated ID uploads).
2. Profile Setup: Once verified, create a rich profile. List services with pricing (fixed/hourly/daily). Upload a structured portfolio via Cloudinary. Set availability on a calendar.
3. Managing Work:
o Receive actionable notifications (email & in-app).
o Manage all client communication and send quotes via chat.
o Create discount codes without admin involvement.
o Approve/decline bookings with one click.
4. Getting Paid:
o View transparent earnings dashboard with real-time statuses: Paid, Pending, Available, Processed.
o Click "Request Payout" to trigger automatic Stripe transfer. (Solves manual payout workflow).
4.3 The Hub Journey (Agency/Coordinator)

1. Onboarding: Similar to Provider, with optional business verification.
2. Project Creation: Create a new project (e.g., "Smith Wedding"). Invite verified providers to join.
3. Coordination: Manage combined schedules, budgets, and team communication in a single dashboard.
4. Client Delivery: Present a unified package to the client for single-payment approval.
4.4 The Admin Journey

1. Role-Based Login: Dedicated panel with tailored permissions (Operations, Support).
2. Verification Queue: Structured list of applicants. View ID and details side-by-side. Approve/reject with one click. Automated email sent.
3. Platform Monitoring: Live dashboard of users, bookings, revenue, and payout requests.
4. Management: Handle users, reported content, support tickets, and create platform-wide coupons.
5. Platform Architecture & Technology Stack

5.1 Frontend

• Framework: React with TypeScript
• State Management: React Context API / Zustand
• Styling: Tailwind CSS
5.2 Backend & Database

• Platform: Supabase
o Provides PostgreSQL database
o Built-in authentication
o Real-time capabilities for chat
o Row Level Security for data protection
5.3 Payments

• Stripe Connect – Handles provider onboarding, payment processing, escrow, commission calculation, and automated disbursements.
5.4 Media Management

• Cloudinary – Manages uploads, storage, optimization, and delivery of all images and videos.
5.5 Email & Communications

• Resend / SendGrid – Sends transactional emails (welcome, booking confirm, payment receipt).
5.6 Architecture Diagram


6. UI/UX Design Integration

• Source of Truth: The approved "PLUG'D 2.0 PLATFORM VISUAL AID" PDF.
• Fidelity: Pixel-perfect implementation of all layouts, styling, and user flows.
• Component Library: A reusable component system will be created based on the design file to ensure consistency.
7. Feature Deep Dive

7.1 Request & Quote System

• Customers post requests with details and budget.
• Requests appear in a feed for relevant providers.
• Providers initiate chat and send formal "Quotes" (custom price, description, expiration).
• Customers compare quotes in a dedicated section and accept one, which auto-creates a booking and prompts payment.
7.2 Booking & Calendar Engine

• Providers set default hours and block unavailable dates.
• Services can be "Instant Book" or "Manual Approval."
• Customers see a color-coded calendar (green = available).
• Selected slots are locked for 15 minutes during checkout to prevent double-booking.
• (Future: External calendar sync – Google/iCal).
7.3 Admin Dashboard & Queues

• Overview: KPIs (new users, pending verifications, pending payouts).
• Verification Queue: List of applicants with approve/reject buttons. Action logs saved.
• Payout Queue: List of payout requests. Primarily automated, with manual override if needed.
• User Management: Search, view details, suspend accounts.
7.4 Coupon & Discount System

• Provider-Created: In dashboard, create coupons with code, type (%, fixed), applicable services, limits, and expiration.
• Customer Application: "Have a discount code?" field at checkout. Valid codes instantly update total.
• Admin Coupons: Global or user-specific coupons from admin panel.
7.5 Payout & Financials Hub

• Provider View:
o Current Balance (available to withdraw)
o Pending Balance (in-progress bookings)
o Payout History (date, amount, status)
o Transaction List (filterable by date, customer, status)
• Admin View: Platform revenue overview, transaction monitoring, reconciliation tools.
8. Testing Strategy

8.1 Testing Levels

• Unit Testing: Individual functions and components (Jest, React Testing Library).
• Integration Testing: Interactions between systems (e.g., approval triggers email).
• End-to-End Testing: Simulated full user journeys (Cypress / Playwright).
8.2 Testing Phases

1. Development Testing: Continuous by developers.
2. Internal QA (Weeks 10-11): Dedicated team testing on staging, logging bugs.
3. User Acceptance Testing (Weeks 11-12): Closed beta with friendly users for final feedback and tweaks.
9. Project Timeline, Milestones & Deliverables (3 Months)

Month 1: Foundation

• Sprint 1 (Weeks 1-2): React + TypeScript setup. Supabase configured. User authentication implemented.
• Sprint 2 (Weeks 3-4): Account-level ID upload via Cloudinary. Admin verification queue built. Approval/rejection workflow with automated emails.
Month 2: Core Marketplace

• Sprint 3 (Weeks 5-6): Service listing form with pricing. Portfolio upload. Visual calendar for availability. Customer-facing service pages. Direct booking flow.
• Sprint 4 (Weeks 7-8): Stripe Connect integration (provider onboarding, payment element). Checkout page. In-app chat (Supabase Realtime). Service Request feature. Quote system (send/accept).
Month 3: MVP Completion & Launch

• Sprint 5 (Weeks 9-10): Enhanced admin dashboard (queues). Automated payout system. Provider coupon tool. Admin coupon management.
• Sprint 6 (Weeks 11-12): Internal QA sprint. User Acceptance Testing. Performance/security review. Final polishing. Production deployment and MVP launch.
10. Success Metrics (KPIs)

• Provider Onboarding Success Rate: % completing sign-up and verification. (Target: >70%)
• Average Verification Time: Time from upload to approval. (Target: <4 hours)
• Booking Conversion Rate: % of service page views leading to paid bookings. (Target: >5%)
• Payout Automation Rate: % of payouts without manual intervention. (Target: >95%)
• User Retention (D1/D7): % returning 1 day and 7 days after sign-up.
• Net Promoter Score (NPS): User satisfaction. (Target: >40)
 

 