# SCMXpertLite - UI Documentation

## Overview
SCMXpertLite is a full-stack supply chain management application with user authentication, shipment tracking, and real-time device streaming capabilities.

---

## Page Structure

### 1. **Login Page** (`/login`)
**Description:** Initial authentication page where users enter their credentials.

**Components:**
- Email input field (type: email, required)
- Password input field (type: password, required)
- "Login" button
- Error message display (red text)
- "New user? Signup" link to signup page

**Functionality:**
- Validates email format
- Sends POST request to `/auth/login` with credentials
- Receives JWT token (`access_token`) from backend
- Stores token in localStorage
- Redirects to Dashboard on success
- Shows error message on failure (e.g., "Invalid credentials")

**Styling:**
- Centered form in a container
- Blue topbar (logout visible only after login)
- White form fields with padding

---

### 2. **Signup Page** (`/signup`)
**Description:** New user registration page.

**Components:**
- Name input field (required)
- Email input field (type: email, required)
- Password input field (type: password, required)
- "Sign up" button
- Error message display (red text)
- "Already have an account? Login" link to login page

**Functionality:**
- Validates all fields are filled
- Sends POST request to `/auth/signup` with user data
- Returns user ID on success
- Redirects to Login page after successful signup
- Shows error message on failure (e.g., "User already exists")

**Styling:**
- Similar to login page
- Container-based layout
- Form fields with consistent styling

---

### 3. **Dashboard Page** (`/`) - Protected Route
**Description:** Main application page showing all shipments.

**Components (Topbar - visible when authenticated):**
- "SCMXpertLite" branding (left side)
- Navigation links (right side):
  - Dashboard link
  - Create link
  - Logout button

**Components (Main Content):**
- H1 heading: "Dashboard"
- "+ Create New Shipment" link button
- Shipments list (unordered list):
  - Each shipment item shows:
    - **Name** (bold)
    - Origin → Destination (with "—" if empty)
    - "Stream" link (click to view device stream)
  - Empty state: "No shipments found." (when no shipments exist)
- Loading state: "Loading..." (while fetching data)

**Functionality:**
- Loads on component mount via `useEffect`
- Fetches shipments from `/shipments` endpoint
- Displays list sorted by creation date (newest first)
- Clicking "Stream" navigates to `/stream/{deviceId}`
- Clicking "+ Create New Shipment" navigates to `/create`

**Styling:**
- Container layout with padding
- List items with links
- Blue topbar with white text
- Light gray background

---

### 4. **Create Shipment Page** (`/create`) - Protected Route
**Description:** Form to create a new shipment.

**Components:**
- H2 heading: "Create Shipment"
- Form fields:
  - Shipment name input (required)
  - Device ID input (required)
  - Origin input (optional)
  - Destination input (optional)
- "Create" button
- Error message display (red text)

**Functionality:**
- Form submission via POST to `/shipments`
- Includes all form fields in request payload
- Redirects to Dashboard (`/`) on success
- Shows error message on failure
- Requires authentication (JWT token in Authorization header)

**Styling:**
- Container layout
- Form inputs with padding
- Blue topbar visible
- Red error messages

---

### 5. **Device Stream Page** (`/stream/:deviceId`) - Protected Route
**Description:** Real-time device data streaming page using WebSocket.

**Components:**
- H2 heading: "Device Stream — {deviceId}"
- Status display: "Status: {connecting|connected|closed|error}"
- Messages container:
  - Empty state: "No messages yet."
  - Displays messages as JSON (pretty-printed)

**Functionality:**
- Connects to WebSocket endpoint: `ws://localhost:8000/ws/{deviceId}?token={token}`
- Validates token via query parameter
- Displays incoming messages in real-time
- Closes connection on component unmount
- Shows connection status (connecting, connected, closed, error)

**Styling:**
- Container layout
- Pre-formatted text for JSON messages
- Small text for status display
- Blue topbar visible

---

## Navigation Flow

```
Start
  ↓
Login Page (/login)
  ├─ New user? → Signup Page (/signup)
  │              ↓ (after signup)
  │              Back to Login
  │
  └─ Existing user → Dashboard (/)
                       ↓
                    ├─ Create New Shipment link → Create Page (/create)
                    │                               ↓ (after create)
                    │                               Back to Dashboard
                    │
                    └─ Stream link (on shipment) → Device Stream (/stream/:deviceId)
                                                    ↓
                                                    Back to Dashboard

Logout: From any page → Login (/login)
```

---

## Authentication & Authorization

**Protected Routes:**
- `/` (Dashboard) - requires token
- `/create` (Create Shipment) - requires token
- `/stream/:deviceId` (Device Stream) - requires token

**Public Routes:**
- `/login` (Login)
- `/signup` (Signup)

**Token Management:**
- Stored in `localStorage` key: `token`
- Set in axios Authorization header: `Bearer {token}`
- JWT token contains user ID and expiration
- On logout: token is removed from localStorage

---

## API Endpoints Used

### Authentication
- `POST /auth/signup` - Register new user
- `POST /auth/login` - Login and receive token

### Shipments (Protected)
- `POST /shipments` - Create new shipment
- `GET /shipments` - Fetch all shipments
- `GET /shipments/{id}` - Fetch single shipment

### Device Stream (Protected)
- `POST /device/publish` - Publish device data
- `WS /ws/{deviceId}` - WebSocket for real-time streaming

---

## UI Specifications

### Colors
- **Primary:** Blue (#007BFF) - topbar background
- **Text:** White (on blue topbar), Black (on white background)
- **Error:** Red (#FF0000) - error messages
- **Background:** Light gray/white

### Typography
- **Headings:** H1, H2 elements
- **Links:** Blue with underline (default HTML styling)
- **Form Fields:** Standard HTML inputs with padding

### Layout
- **Container:** Max-width container with padding
- **Topbar:** Full-width blue bar (fixed height, 40-50px)
- **Navigation:** Flex layout with "auto" margin-left for right alignment
- **Forms:** Vertical stack with spacing between fields

---

## State Management

### App Component State
- `isAuth` - boolean indicating if user is authenticated
- `loading` - boolean for initial auth check

### Page Component States
- **Login:** `form` (email, password), `err`
- **Signup:** `form` (name, email, password), `err`
- **Dashboard:** `shipments` (array), `loading`
- **Create Shipment:** `form` (name, deviceId, origin, destination), `err`
- **Device Stream:** `messages` (array), `status` (connecting|connected|closed|error)

---

## Error Handling

**Common Error Messages:**
- "Invalid credentials" - wrong email/password
- "User already exists" - email already registered
- "Create failed" - shipment creation error
- "Database not initialized" - backend connection issue
- "No token returned from server" - auth server issue

---

## User Flow Examples

### New User Journey
1. Open app → See Login page
2. Click "Signup"
3. Fill name, email, password
4. Click "Sign up"
5. Redirected to Login page
6. Enter email and password
7. Click "Login"
8. See Dashboard with topbar
9. Click "+ Create New Shipment"
10. Fill shipment details
11. Click "Create"
12. Redirected to Dashboard, see new shipment in list

### Existing User Journey
1. Open app → See Login page (first time)
2. Enter email and password
3. Click "Login"
4. See Dashboard
5. Click "Stream" on a shipment
6. See Device Stream page with real-time data
7. Click "Dashboard" in topbar
8. Back to Dashboard
9. Click "Logout"
10. Redirected to Login page

---

## Responsive Design Considerations

- Mobile: Stack form fields vertically
- Tablet: Same as mobile with wider containers
- Desktop: Optimized with flexbox layouts

---

## Future Enhancements

- [ ] Logout confirmation modal
- [ ] Shipment edit/delete functionality
- [ ] User profile page
- [ ] Shipment filtering/search
- [ ] Dark mode toggle
- [ ] Mobile app version
- [ ] Email notifications
- [ ] CSV export for shipments

---

**Version:** 1.0.0  
**Last Updated:** December 4, 2025  
**Author:** SCMXpertLite Team
