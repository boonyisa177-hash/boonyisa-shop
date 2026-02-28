# Review System Implementation - สามัญฐานรีวิวจากผู้เข้าพัก

## Overview
The hotel booking system now includes a comprehensive review system with image support. Guests can submit reviews with photos, and all reviews are persisted in the database.

## Features Implemented

### 1. **Database Model (Review)**
- Added `Review` model to store reviews persistently
- Columns:
  - `id`: Primary key
  - `room_id`: Foreign key to Room
  - `name`: Reviewer's name (defaults to 'Anonymous')
  - `rating`: Rating 1-5 stars
  - `comment`: Review text
  - `image`: Image filename (stored in static/uploads/)
  - `created_at`: Timestamp

### 2. **Review Submission**
- **Endpoint**: POST `/review/<room_id>`
- **Features**:
  - Accept reviewer name (optional, defaults to "Anonymous")
  - Accept star rating (1-5, validated)
  - Accept text comment (required - validation added)
  - Support image upload (PNG, JPG, JPEG, GIF, WEBP)
  - Automatic unique filename generation for uploaded images
  - Max file size: 5 MB
  - Reviews saved to database for persistence
  - Session backup for backward compatibility

### 3. **Review Display**
- **Page**: `/reviews` (accessible via navbar "📝 รีวิว")
- **Features**:
  - Display reviews grouped by room
  - Show reviewers' names and ratings (in stars)
  - Display review text
  - **Display images** if attached to reviews
  - Show review timestamp
  - Only rooms with reviews are displayed

### 4. **Image Management**
- **Upload Path**: `static/uploads/`
- **Filename Format**: `review_{uuid}_{timestamp}.{ext}`
- **Supported Formats**: PNG, JPG, JPEG, GIF, WEBP
- **Max Size**: 5 MB
- **Delete Endpoint**: POST `/delete-review-image/<room_id>/<review_index>`
  - Removes image file from disk
  - Clears image reference in database

### 5. **Integration Points**

#### Booking Form (templates/booking_form.html)
- Review form section included below booking form
- Shows existing reviews for the room
- Displays images with reviews
- Image preview before submission
- Reviews visible immediately after submission

#### Main Index (templates/index.html)
- Shows review count and average rating for each room
- Rating displayed as stars

#### Admin (templates/admin.html/admin_bookings.html)
- Can view all guest reviews from database
- Database shows all persistent reviews

## Usage

### Submitting a Review
1. Go to booking form for any room
2. Scroll down to review section
3. Enter name (optional)
4. Select rating (1-5 stars)
5. Write review comment
6. Upload image (optional)
7. Click "ส่งรีวิว" button

### Viewing All Reviews
1. Click "📝 รีวิว" in navigation menu
2. See all reviews grouped by room with images

### Deleting Images
- Click ✕ button on the image in review
- Image deleted from disk and database

## Technical Details

### Database Schema
```
review (table)
├── id (INTEGER, PRIMARY KEY)
├── room_id (INTEGER, FOREIGN KEY)
├── name (VARCHAR(200))
├── rating (INTEGER)
├── comment (TEXT)
├── image (VARCHAR(500))
└── created_at (DATETIME)
```

### Backward Compatibility
- Session-based reviews still supported alongside database reviews
- All data types and formats preserved
- No breaking changes to existing functionality

### File Storage
- Images physically stored in `static/uploads/`
- Unique filenames prevent conflicts
- Automatic cleanup when images deleted

## Validation & Error Handling
- Rating validation: 1-5 scale enforced
- Comment validation: Required field
- Image validation: File type and size checked
- Proper error messages in Thai language
- Graceful fallback for missing data

## Security Considerations
- Filenames sanitized with `secure_filename()`
- File type whitelist enforced
- File size limit enforced (5 MB)
- CSRF protection via session handling

## Next Steps (Optional)
- Add admin approval/moderation for reviews
- Add search/filter reviews by rating
- Add export reviews functionality
- Implement review response from hotel
- Add review helpful/unhelpful voting

## Testing Checklist
✓ Database initialization with Review model
✓ Image upload and storage
✓ Review persistence in database
✓ Review display with images
✓ Image deletion functionality
✓ Thai language support
✓ Navigation menu linkage
✓ Backward compatibility with session reviews
