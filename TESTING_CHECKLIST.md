# Local Testing Checklist - Business Reporter File Exchange Portal

## Server Information
- **Local URL**: http://localhost:5000 or http://127.0.0.1:5000
- **Status**: Running ✅

## Available Test Users

From database:
| Username | Role | Password | Test For |
|----------|------|----------|----------|
| ivantomic | super | ? | Full admin access |
| tomicivan-admin | admin | ? | Admin permissions |
| test | user | ? | Regular user |
| ukuser | country_user_uk | ? | UK file filtering |
| deuser | country_user_de | ? | DE file filtering |
| ituser | country_user_it | ? | IT file filtering |
| fruser | country_user_fr | ? | FR file filtering |
| esuser | country_user_es | ? | ES file filtering |

## Core Testing Steps

### 1. Authentication Flow ✅
- [ ] **Login**
  - Navigate to http://localhost:5000
  - Should redirect to /login
  - Try invalid credentials → should show error
  - Login with valid credentials → should redirect to main page
  - Verify username appears in UI
  - Verify role-based navigation shows correct items

- [ ] **Logout**
  - Click logout button
  - Should redirect to /login
  - Try accessing protected page → should redirect back to login

### 2. Main File Listing Page ✅
- [ ] **Visual Display**
  - Files should be listed with names, sizes, upload dates
  - Country badges should display correctly
  - Urgency indicators (High = red, Normal = green)
  - Stage indicators should show correctly
  
- [ ] **Filtering**
  - Country filter dropdown should work
  - Stage filter should work
  - Search functionality (if present)

### 3. File Operations ✅
- [ ] **Download**
  - Click download on a file
  - Should download successfully
  - Filename should be correct
  - File content should be intact

- [ ] **View Details** (if modal exists)
  - Click file to see details
  - Metadata should display correctly
  - Close modal should work

### 4. File Upload ✅ (Super/Admin only)
- [ ] **Upload Process**
  - Click upload button
  - Select a test file (.zip, .docx, or .pdf)
  - Fill in metadata (country, urgency, stage)
  - Submit → should show success message
  - File should appear in listing immediately
  - File should appear in correct directory (files/)

- [ ] **Upload Validation**
  - Try uploading disallowed file type → should reject
  - Try uploading file over size limit → should reject
  - Try uploading with missing required fields → should reject

### 5. Archive Functionality ✅ (Super/Admin only)
- [ ] **Archive File**
  - Click archive on a file
  - Should move to archive
  - Should disappear from main listing
  - Should appear in /archive page

- [ ] **Restore File**
  - Go to /archive page
  - Click restore on archived file
  - Should return to main listing
  - Should disappear from archive

### 6. Approve/Unapprove ✅ (Super/Admin only)
- [ ] **Approve**
  - Click approve on a file
  - Should move to files/_approved/
  - Badge/indicator should show "Approved"

- [ ] **Unapprove**
  - Click unapprove on approved file
  - Should move back to files/
  - Badge should disappear

### 7. Publication Status ✅ (if applicable)
- [ ] **Update Publication Status**
  - Change publication status on a file
  - Should update immediately
  - Should persist after page refresh

### 8. Admin Features ✅ (Admin/Super only)
- [ ] **User Management** (/admin/users)
  - Navigate to admin page
  - See list of all users
  - Create new user → should succeed
  - Edit user role → should persist
  - Delete user → should remove from database
  - Reset password → should allow login with new password
  - Activate/deactivate user → should block/enable login

- [ ] **Invite Management** (Super only)
  - Create invite code
  - Should generate unique code
  - Copy invite code
  - Use code to register → should succeed
  - Code should become invalid after use
  - Revoke invite → should become unusable

### 9. Country-Specific Filtering ✅
- [ ] **Country Users**
  - Login as country_user_uk
  - Should ONLY see UK files
  - Login as country_user_de
  - Should ONLY see DE files
  - Verify they can't see files from other countries

- [ ] **Regular Users**
  - Login as regular 'user' or 'admin'
  - Should see ALL files from all countries
  - Country filter should work

### 10. Email Notifications ✅ (if configured)
- [ ] **File Upload Notification**
  - Upload a file with urgency set
  - Check configured email inbox
  - Should receive notification email
  - Email should contain file details

### 11. UI/UX ✅
- [ ] **Responsive Design**
  - Test on different browser windows
  - Mobile view should work
  - Dark/light theme toggle (if present)

- [ ] **Flash Messages**
  - Successful operations should show success messages
  - Errors should show error messages
  - Messages should disappear after a few seconds

### 12. Audit Logging ✅
- [ ] **Verify Logging**
  - Check audit.log file
  - Login event should be logged
  - Logout event should be logged
  - File upload should be logged
  - Admin actions should be logged

### 13. Error Handling ✅
- [ ] **404 Errors**
  - Navigate to non-existent page
  - Should show friendly error page

- [ ] **403 Errors**
  - Try accessing admin page as regular user
  - Should be blocked

- [ ] **Session Expiry**
  - Leave browser idle
  - Try performing action
  - Should redirect to login if session expired

### 14. Performance ✅
- [ ] **Page Load Speed**
  - Main page should load in <2 seconds
  - File listing should load quickly
  - Download should start promptly

- [ ] **Concurrent Sessions**
  - Open multiple browser tabs
  - Login as different users
  - Actions shouldn't interfere with each other

## Critical Issues to Watch For

⚠️ **Security**
- Users can access other users' files without permission
- SQL injection in search/filter
- XSS in user input
- Session hijacking possible

⚠️ **Functionality**
- Files not uploading/saving
- Download links broken
- Role permissions not enforced
- Database corruption

⚠️ **Performance**
- Slow page loads
- Memory leaks
- Database locking issues

## Test Results Template

```
Date: ___________
Tester: ___________

✅ Passed Tests: __/14
❌ Failed Tests: __/14
⚠️ Warnings: _____

Key Findings:
- [ ] All core features work
- [ ] No critical bugs found
- [ ] Performance acceptable
- [ ] Security verified

Notes:
_________________________________
_________________________________

```

## Post-Testing

After completing tests:
1. Review audit.log for any errors
2. Check database integrity
3. Verify no files in wrong directories
4. Document any bugs found
5. Note any UI/UX improvements needed

