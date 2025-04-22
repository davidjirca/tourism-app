# Docker Deployment Guide for Travel App

This guide explains how to deploy the Travel Recommendation & Price Alert System using Docker and Docker Compose.

## Prerequisites

- Docker Engine (version 19.03 or later)
- Docker Compose (version 1.27 or later)
- Git (to clone the repository)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/travel-app.git
cd travel-app
```

### 2. Configure Environment Variables

Copy the example environment file and update it with your actual API keys:

```bash
cp .env.example .env
```

Edit the `.env` file with your actual API credentials:
- OpenWeather API key
- Skyscanner API key
- Numbeo API key
- Twilio credentials (for SMS notifications)
- Email credentials (for email notifications)

### 3. Build and Start the Services

```bash
docker-compose up -d
```

This command will:
- Build the application image
- Start all required services (app, Celery workers, PostgreSQL, Redis, etc.)
- Initialize the database
- Configure periodic tasks

### 4. Verify the Deployment

Once all containers are running, you can access:

- The API documentation: http://localhost:8000/docs
- PgAdmin (PostgreSQL management): http://localhost:5050
  - Login with: admin@travel.com / admin
- Flower (Celery task monitoring): http://localhost:5555

## Container Architecture

The deployment consists of the following containers:

- **app**: The FastAPI application serving the API
- **celery-worker**: Processes background tasks like price checks
- **celery-beat**: Schedules periodic tasks
- **flower**: Monitors Celery tasks
- **postgres**: PostgreSQL database for persistent storage
- **redis**: Redis for caching and message broker
- **pgadmin**: Web interface for PostgreSQL management

## Scaling the Application

To scale the Celery workers:

```bash
docker-compose up -d --scale celery-worker=3
```

## Logs and Troubleshooting

To check logs for a specific service:

```bash
docker-compose logs -f app
docker-compose logs -f celery-worker
```

## Stopping the Application

To stop all services:

```bash
docker-compose down
```

To stop and remove all data volumes (WARNING: this will delete all database data):

```bash
docker-compose down -v
```

## Production Considerations

For production deployments, consider:

1. Using a dedicated Redis instance for caching and another for Celery
2. Setting up proper database backups
3. Configuring HTTPS with a reverse proxy (Nginx or Traefik)
4. Implementing proper secrets management
5. Setting up monitoring and alerting

# Authentication System Documentation

This document explains the authentication system implemented in the Travel App.

## Overview

The authentication system uses JWT (JSON Web Tokens) to secure API endpoints and manage user sessions. The system provides:

- User registration
- User login with token generation
- Secure password hashing
- Token validation for protected routes
- User profile management

## Authentication Flow

1. **Registration**: Users register with email and password
2. **Login**: Users provide credentials and receive a JWT token
3. **API Access**: Protected API endpoints require a valid JWT token
4. **Token Validation**: The system validates tokens on each request

## API Endpoints

### Public Endpoints

- `POST /auth/register` - Create a new user account
- `POST /auth/login` - Authenticate and receive a JWT token
- `GET /destinations/` - View all destinations (accessible to everyone)
- `GET /destinations/{destination_id}` - View a specific destination (accessible to everyone)

### Protected Endpoints

- `GET /auth/me` - Get current user profile
- `PUT /auth/me` - Update user profile
- `POST /auth/change-password` - Change user password
- `GET /destinations/{destination_id}/price_history` - View price history (requires authentication)
- `POST /alerts/` - Create price alerts (requires authentication)
- `GET /alerts/` - List user's price alerts (requires authentication)
- `PUT /alerts/{alert_id}` - Update an alert (requires authentication)
- `DELETE /alerts/{alert_id}` - Delete an alert (requires authentication)
- `POST /destinations/{destination_id}/favorite` - Add a destination to favorites
- `DELETE /destinations/{destination_id}/favorite` - Remove a destination from favorites
- `GET /favorites` - Get user's favorite destinations