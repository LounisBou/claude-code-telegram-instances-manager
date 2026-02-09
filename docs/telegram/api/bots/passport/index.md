# Telegram Passport

Handle encrypted personal documents shared by users for identity verification.

## Methods

### setPassportDataErrors

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | Integer | Yes | User who sent the Passport data |
| errors | Array of PassportElementError | Yes | Errors found in the data |

**Returns:** True

## Types

### PassportData

| Field | Type | Description |
|-------|------|-------------|
| data | Array of EncryptedPassportElement | Array of encrypted passport elements |
| credentials | EncryptedCredentials | Encrypted credentials for decryption |

### EncryptedPassportElement

| Field | Type | Description |
|-------|------|-------------|
| type | String | Element type: "personal_details", "passport", "driver_license", "identity_card", "internal_passport", "address", "utility_bill", "bank_statement", "rental_agreement", "passport_registration", "temporary_registration", "phone_number", "email" |
| data | String | Base64-encoded encrypted data (optional) |
| phone_number | String | User's phone number (optional) |
| email | String | User's email (optional) |
| files | Array of PassportFile | Array of encrypted files (optional) |
| front_side | PassportFile | Encrypted front side document (optional) |
| reverse_side | PassportFile | Encrypted reverse side document (optional) |
| selfie | PassportFile | Encrypted selfie with document (optional) |
| translation | Array of PassportFile | Array of encrypted translated documents (optional) |
| hash | String | Base64-encoded element hash for setPassportDataErrors |

### PassportFile

| Field | Type | Description |
|-------|------|-------------|
| file_id | String | Identifier for downloading |
| file_unique_id | String | Unique identifier |
| file_size | Integer | File size in bytes |
| file_date | Integer | Unix time when file was uploaded |

### EncryptedCredentials

| Field | Type | Description |
|-------|------|-------------|
| data | String | Base64-encoded encrypted JSON with all credentials |
| hash | String | Base64-encoded data hash for verification |
| secret | String | Base64-encoded encrypted secret for decryption |

### PassportElementError variants

- **PassportElementErrorDataField**: source="data", type, field_name, data_hash, message
- **PassportElementErrorFrontSide**: source="front_side", type, file_hash, message
- **PassportElementErrorReverseSide**: source="reverse_side", type, file_hash, message
- **PassportElementErrorSelfie**: source="selfie", type, file_hash, message
- **PassportElementErrorFile**: source="file", type, file_hash, message
- **PassportElementErrorFiles**: source="files", type, file_hashes (Array), message
- **PassportElementErrorTranslationFile**: source="translation_file", type, file_hash, message
- **PassportElementErrorTranslationFiles**: source="translation_files", type, file_hashes (Array), message
- **PassportElementErrorUnspecified**: source="unspecified", type, element_hash, message

## Gotchas

- All data is encrypted with the bot's public RSA key -- decryption requires the private key
- Credentials decryption chain: decrypt credentials.secret with RSA, then decrypt credentials.data with AES, then get per-element keys, then decrypt element data with AES
- setPassportDataErrors: informs user which fields need correction. User will see errors in Telegram.
- Passport data is only accessible once per user request -- store it if needed
- Bot must be configured for Passport via @BotFather
