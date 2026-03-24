# Supabase Backend Setup for P2P Secure-Lend Kenya

This document explains how to set up and use Supabase as the complete backend for the P2P lending platform.

## Overview

The system has been refactored to use Supabase as the primary database and authentication backend instead of Django's ORM and SQLite. This provides:

- Cloud-hosted PostgreSQL database
- Real-time capabilities
- Built-in authentication
- Row Level Security (RLS)
- REST API access
- Better scalability

## Setup Steps

### 1. Database Setup

Run the complete setup SQL in your Supabase SQL Editor:

```sql
-- Run this file in Supabase SQL Editor
supabase_complete_setup.sql
```

This will:
- Create all necessary tables (users, loans, collateral, investments, etc.)
- Set up indexes for performance
- Create business logic functions
- Enable Row Level Security
- Create the admin user (sammyseth260@gmail.com)

### 2. Environment Configuration

Your `.env` file should contain:

```env
SUPABASE_URL=https://ffxdkifwaxgaojlyppmg.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SECRET_KEY=your_django_secret_key
DEBUG=True
```

### 3. Test the Connection

Run the test command to verify everything is working:

```bash
python manage.py test_supabase
```

### 4. Create Admin User (if needed)

If the admin user wasn't created automatically:

```bash
python manage.py create_admin
```

## Architecture Changes

### Authentication Flow

1. **SupabaseAuthBackend**: Primary authentication against Supabase
2. **CustomAuthBackend**: Fallback for Django admin
3. **ModelBackend**: Final fallback

### Data Flow

1. All user registration goes directly to Supabase
2. Authentication checks Supabase first
3. Django users are created/updated from Supabase data for session management
4. All business operations use Supabase services

### Key Components

#### Services Layer (`core/services.py`)
- `SupabaseService`: Main service class
- `LoanCalculatorService`: Business logic calculations
- Individual service classes for each entity

#### Supabase Client (`core/supabase_client.py`)
- `SupabaseClient`: Low-level API client
- `SupabaseUserService`: User operations
- `SupabaseCollateralService`: Collateral operations
- `SupabaseLoanService`: Loan operations
- `SupabaseInvestmentService`: Investment operations

#### Authentication (`core/backends.py`)
- `SupabaseAuthBackend`: Authenticates against Supabase
- `CustomAuthBackend`: Fallback authentication

## Database Schema

### Users Table
- Stores all user information including role, wallet balance, etc.
- Supports roles: borrower, lender, agent, admin
- Includes admin promotion flags

### Collateral Table
- Links to users
- Tracks verification status and verified_by agent

### Loans Table
- Links borrower and collateral
- Tracks funding status and loan lifecycle

### Investments Table
- Links lenders to loans
- Prevents duplicate investments

### Additional Tables
- `wallet_transactions`: Transaction history
- `commissions`: Agent commissions
- `payments`: Loan payments

## Admin User Setup

The admin user `sammyseth260@gmail.com` is automatically:
1. Created during database setup
2. Promoted when logging in (if exists with different role)
3. Granted full admin privileges

## Key Features

### Automatic Admin Promotion
Users with email `sammyseth260@gmail.com` are automatically promoted to admin role.

### Logout Fix
Custom logout view handles both GET and POST requests to fix the 405 error.

### Real-time Data
All operations go directly to Supabase, ensuring real-time data consistency.

### Business Logic
Loan calculations (30/50 rule, fees, interest) are implemented as PostgreSQL functions.

## Usage Examples

### Creating a User
```python
from core.services import supabase_service

user = supabase_service.create_user(
    username="testuser",
    email="test@example.com",
    password="password123",
    role="borrower",
    phone_number="254712345678",
    national_id="12345678"
)
```

### Getting User Data
```python
user = supabase_service.get_user_by_username("testuser")
user_by_email = supabase_service.get_user_by_email("test@example.com")
```

### Creating a Loan
```python
loan = supabase_service.create_loan(
    borrower_id=user_id,
    collateral_id=collateral_id,
    principal_amount=50000.00,
    duration_months=6
)
```

## Troubleshooting

### Connection Issues
1. Verify SUPABASE_URL and SUPABASE_ANON_KEY in .env
2. Check Supabase project status
3. Run `python manage.py test_supabase`

### Authentication Issues
1. Check if user exists in Supabase
2. Verify authentication backends in settings
3. Check logs for authentication errors

### Admin Access Issues
1. Verify admin user exists: `SELECT * FROM users WHERE role = 'admin'`
2. Check email matches exactly: `sammyseth260@gmail.com`
3. Run admin creation command if needed

## Security Notes

- Row Level Security (RLS) is enabled but currently permissive
- In production, implement proper RLS policies
- Use Supabase Auth for production authentication
- Rotate API keys regularly
- Enable database backups

## Migration from Django ORM

The system maintains Django models for compatibility but all operations go through Supabase. This allows:
- Gradual migration
- Django admin compatibility
- Session management
- Existing code compatibility

## Next Steps

1. Run the database setup SQL
2. Test the connection
3. Verify admin user access
4. Test user registration and login
5. Implement additional business logic as needed