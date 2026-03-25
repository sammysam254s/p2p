# P2P Secure-Lend Kenya

A Peer-to-Peer Lending Platform where loans are secured by physical collateral, built with Django and Supabase.

## Features

- **Secure Lending**: All loans backed by physical collateral (30/50 rule)
- **High Returns**: 13% monthly interest for lenders
- **Quick Process**: Fast verification through station agents
- **Mobile-First**: Responsive design optimized for mobile devices
- **Real-time**: Built with Supabase for real-time updates

## Tech Stack

- **Backend**: Django 6.0.3, Python 3.11+
- **Database**: Supabase (PostgreSQL)
- **Frontend**: Bootstrap 5, Vanilla JavaScript
- **Deployment**: Render
- **Styling**: Custom green theme with Bootstrap

## Business Logic

### The 30/50 Rule
1. **Devaluation**: Market value reduced by 30%
2. **Loan Limit**: Maximum loan is 50% of devalued amount
3. **Example**: KES 100,000 item → KES 70,000 (devalued) → KES 35,000 (max loan)

### Financial Terms
- **Interest Rate**: 13% per month (flat rate)
- **Platform Fee**: 1% of principal amount
- **Insurance Fee**: 1% of principal amount
- **Funding Window**: 7 days from listing

## User Roles

### Borrowers
1. Submit collateral details and loan application
2. Visit station agent for physical verification
3. Loan gets listed on marketplace
4. Receive funds when fully funded

### Lenders
1. Browse verified loan opportunities
2. Review collateral and terms
3. Invest from KES 100 upwards
4. Earn 13% monthly returns

### Station Agents
1. Physically verify collateral items
2. Update verification status
3. Enable loans to be listed

## Setup Instructions

### 1. Supabase Setup

1. Create a new Supabase project
2. Go to SQL Editor in your Supabase dashboard
3. Run the SQL from `supabase_tables_only.sql` to create tables
4. (Optional) Run `supabase_schema.sql` for full schema with RLS policies

### 2. Local Development

```bash
# Clone the repository
git clone <your-repo-url>
cd p2p-secure-lend

# Install dependencies
pip install -r requirements.txt

# Create .env file
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SECRET_KEY=your_django_secret_key
DEBUG=True

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### 3. Render Deployment

#### Option A: Using render.yaml (Recommended)
1. Fork this repository
2. Connect your GitHub repo to Render
3. Render will automatically detect the `render.yaml` file
4. Update environment variables in Render dashboard

#### Option B: Manual Setup
1. Create new Web Service on Render
2. Connect your GitHub repository
3. Set build command: `./build.sh`
4. Set start command: `gunicorn secure_lend.wsgi:application`
5. Add environment variables:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_ANON_KEY`: Your Supabase anon key
   - `SECRET_KEY`: Django secret key (auto-generated)
   - `DEBUG`: false

## Environment Variables

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SECRET_KEY=your_django_secret_key
DEBUG=False
```

## API Endpoints

- `/` - Home page
- `/register/` - User registration
- `/login/` - User login
- `/borrower/` - Borrower dashboard
- `/agent/` - Station agent panel
- `/marketplace/` - Lender marketplace
- `/loan/<id>/` - Loan details

## Database Schema

### Users
- `id` (UUID, Primary Key)
- `username` (String, Unique)
- `email` (String)
- `role` (borrower/lender/agent)
- `phone_number` (String)
- `national_id` (String, Unique)

### Collateral
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key)
- `item_type` (String)
- `brand_model` (String)
- `market_value` (Decimal)
- `status` (pending/verified/released)

### Loans
- `id` (UUID, Primary Key)
- `borrower_id` (UUID, Foreign Key)
- `collateral_id` (UUID, Foreign Key)
- `principal_amount` (Decimal)
- `interest_rate` (Decimal, default 13%)
- `duration_months` (Integer)
- `funded_amount` (Decimal)
- `status` (pending_collateral/listed/active/paid/cancelled)

### Investments
- `id` (UUID, Primary Key)
- `lender_id` (UUID, Foreign Key)
- `loan_id` (UUID, Foreign Key)
- `amount_invested` (Decimal)
- `date` (Timestamp)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support, email support@p2psecurelend.co.ke or create an issue in this repository.

## Demo Accounts

After running the sample data SQL:
- **Borrower**: demo_borrower / password
- **Lender**: demo_lender / password  
- **Agent**: demo_agent / password

## Security Notes

- All sensitive data is stored in environment variables
- Supabase handles authentication and authorization
- Row Level Security (RLS) policies protect user data
- HTTPS enforced in production
- CSRF protection enabled

## Roadmap

- [ ] SMS notifications via Africa's Talking
- [ ] M-Pesa integration for payments
- [ ] Mobile app (React Native)
- [ ] Advanced analytics dashboard
- [ ] Automated loan scoring
- [ ] Multi-language support (Swahili)