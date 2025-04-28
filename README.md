# Travel Recommendation & Price Alert System

A comprehensive travel platform that helps users discover travel destinations, monitor flight prices, receive personalized recommendations, and plan their trips. The system combines real-time data from external APIs with user preferences to deliver a personalized travel planning experience.

## 🚀 Features

- **Destination Discovery**: Browse destinations with real-time pricing and detailed information
- **Price Tracking**: Monitor flight and hotel prices for your favorite destinations
- **Price Alerts**: Set custom price thresholds and receive notifications via email, SMS, or push
- **User Authentication**: Secure JWT-based authentication system
- **Favorites Management**: Save and organize your favorite destinations
- **Personalized Recommendations**: Get destination suggestions based on your preferences
- **Real-time Data**: Weather, price, and safety information from external APIs

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.9+
- **Database**: PostgreSQL 13
- **Cache & Message Queue**: Redis 6
- **Task Queue**: Celery
- **Authentication**: JWT, Passlib/BCrypt
- **Containerization**: Docker, Docker Compose
- **Monitoring**: Flower, structured logging
- **API Integrations**: OpenWeather, Skyscanner, Numbeo, Twilio

## 🏗️ Architecture

The application uses a containerized microservices architecture with the following components:

- FastAPI web server for the REST API
- Celery workers for background tasks
- PostgreSQL for persistent data storage
- Redis for caching and message broker
- WebSockets for real-time notifications

## 🚀 Getting Started

### Prerequisites

- Docker Engine (19.03+)
- Docker Compose (1.27+)
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/travel-app.git
   cd travel-app
   ```

2. Configure environment variables:
   ```bash
   cp .env.variables .env
   # Edit .env with your API keys and settings
   ```

3. Build and start the services:
   ```bash
   docker-compose up -d
   ```

4. Access the application:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Celery Monitoring: http://localhost:5555
   - PgAdmin: http://localhost:5050 (admin@travel.com / admin)

## 📚 API Documentation

The API documentation is available at `/docs` when the application is running. It provides detailed information about all endpoints, request/response schemas, and authentication methods.

### Main Endpoints

- `POST /auth/register` - Create a new user account
- `POST /auth/login` - Authenticate and get an access token
- `GET /destinations/` - List all travel destinations
- `GET /recommendations/` - Get personalized destination recommendations
- `POST /alerts/` - Create price drop alerts
- `GET /health/` - Check system health

## 🧪 Testing

To run the tests:

```bash
# Run unit tests
docker-compose exec app pytest tests/unit

# Run integration tests
docker-compose exec app pytest tests/integration

# Run with coverage
docker-compose exec app pytest --cov=app tests/
```

## 📦 Deployment

For production deployment, additional steps are recommended:

1. Use a strong secret key for JWT encryption
2. Configure proper CORS settings
3. Set up HTTPS with a reverse proxy (Nginx/Traefik)
4. Implement database backups
5. Configure monitoring and alerting

## 🔒 Security Features

- JWT-based authentication
- Secure password hashing with bcrypt
- Rate limiting to prevent abuse
- Security headers
- Input validation with Pydantic
- Connection pooling for database access
- Structured logging for audit trails

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🧑‍💻 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request