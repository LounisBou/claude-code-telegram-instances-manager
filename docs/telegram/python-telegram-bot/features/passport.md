# Passport

> Telegram Passport -- receive verified identity documents and personal data from users with end-to-end encryption.

## Overview

Telegram Passport allows bots to request identity documents (passport, driver's license, etc.) and personal data from users. Data is encrypted end-to-end: Telegram cannot read it. The bot provides a private RSA key to decrypt the data. Users authorize sharing via a Telegram UI, and the bot receives `PassportData` in an update. Configure Passport via @BotFather and generate an RSA key pair.

## Quick Usage

```python
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

async def handle_passport(update: Update, context: ContextTypes.DefaultType):
    passport_data = update.message.passport_data
    for element in passport_data.decrypted_data:
        if element.type == "personal_details":
            personal = element.decrypted_data  # PersonalDetails object
            print(f"Name: {personal.first_name} {personal.last_name}")

app = (
    Application.builder()
    .token("TOKEN")
    .private_key(open("private.key", "rb").read())
    .build()
)
app.add_handler(MessageHandler(filters.PASSPORT_DATA, handle_passport))
app.run_polling()
```

## Key Classes

### `telegram.PassportData`

Top-level container received in `message.passport_data`.

| Attribute | Type | Description |
|---|---|---|
| `data` | `list[EncryptedPassportElement]` | Encrypted elements shared by the user. |
| `credentials` | `EncryptedCredentials` | Encrypted credentials for decryption. |

| Property | Type | Description |
|---|---|---|
| `decrypted_data` | `list[EncryptedPassportElement]` | Decrypted elements (requires private key on Bot). Elements have `decrypted_data` and `decrypted_files` populated. |
| `decrypted_credentials` | `Credentials` | Decrypted credentials object. |

---

### `telegram.EncryptedPassportElement`

| Attribute | Type | Description |
|---|---|---|
| `type` | `str` | Element type -- see table below. |
| `data` | `str \| None` | Base64-encoded encrypted data (for data-bearing types). |
| `phone_number` | `str \| None` | Plaintext phone number (for `"phone_number"` type). |
| `email` | `str \| None` | Plaintext email (for `"email"` type). |
| `files` | `list[PassportFile] \| None` | Encrypted files (utility bills, etc.). |
| `front_side` | `PassportFile \| None` | Encrypted front side of document. |
| `reverse_side` | `PassportFile \| None` | Encrypted reverse side of document. |
| `selfie` | `PassportFile \| None` | Encrypted selfie with document. |
| `translation` | `list[PassportFile] \| None` | Encrypted translation files. |
| `hash` | `str` | Element hash for error reporting. |

**Element types:**

| Type | Data class | Has files | Has front/reverse | Has selfie |
|---|---|---|---|---|
| `"personal_details"` | `PersonalDetails` | No | No | No |
| `"passport"` | `IdDocumentData` | No | front | Yes |
| `"driver_license"` | `IdDocumentData` | No | front + reverse | Yes |
| `"identity_card"` | `IdDocumentData` | No | front + reverse | Yes |
| `"internal_passport"` | `IdDocumentData` | No | front | Yes |
| `"address"` | `ResidentialAddress` | No | No | No |
| `"utility_bill"` | -- | Yes | No | Yes |
| `"bank_statement"` | -- | Yes | No | Yes |
| `"rental_agreement"` | -- | Yes | No | Yes |
| `"passport_registration"` | -- | Yes | No | Yes |
| `"temporary_registration"` | -- | Yes | No | Yes |
| `"phone_number"` | -- (plaintext) | No | No | No |
| `"email"` | -- (plaintext) | No | No | No |

---

### `telegram.EncryptedCredentials`

| Attribute | Type | Description |
|---|---|---|
| `data` | `str` | Base64-encoded encrypted JSON with per-element decryption keys. |
| `hash` | `str` | Hash for data authentication. |
| `secret` | `str` | Base64-encoded encrypted secret. |

---

### Decrypted Data Types

#### `telegram.Credentials`

Top-level decrypted credentials. Contains `secure_data` (`SecureData`) with per-element keys.

#### `telegram.PersonalDetails`

| Attribute | Type |
|---|---|
| `first_name` | `str` |
| `last_name` | `str` |
| `middle_name` | `str \| None` |
| `date_of_birth` | `str` |
| `gender` | `str` |
| `country_code` | `str` |
| `residence_country_code` | `str` |

#### `telegram.ResidentialAddress`

| Attribute | Type |
|---|---|
| `street_line1` | `str` |
| `street_line2` | `str` |
| `city` | `str` |
| `state` | `str` |
| `country_code` | `str` |
| `post_code` | `str` |

#### `telegram.IdDocumentData`

| Attribute | Type |
|---|---|
| `document_no` | `str` |
| `expiry_date` | `str \| None` |

---

### `telegram.PassportFile`

| Attribute | Type | Description |
|---|---|---|
| `file_id` | `str` | File identifier for downloading. |
| `file_unique_id` | `str` | Unique file identifier. |
| `file_size` | `int` | File size in bytes. |
| `file_date` | `int` | Unix timestamp of when the file was uploaded. |

---

### Passport Error Types

Used with `set_passport_data_errors` to inform users of validation problems. All require `source`, `type`, `message`, and additional params depending on the error kind.

| Class | Additional Params | Description |
|---|---|---|
| `PassportElementErrorDataField` | `field_name, data_hash` | Error in a specific data field. |
| `PassportElementErrorFile` | `file_hash` | Error in an uploaded file. |
| `PassportElementErrorFiles` | `file_hashes` | Error in uploaded files (list). |
| `PassportElementErrorFrontSide` | `file_hash` | Error in front side scan. |
| `PassportElementErrorReverseSide` | `file_hash` | Error in reverse side scan. |
| `PassportElementErrorSelfie` | `file_hash` | Error in selfie. |
| `PassportElementErrorTranslationFile` | `file_hash` | Error in a translation file. |
| `PassportElementErrorTranslationFiles` | `file_hashes` | Error in translation files (list). |
| `PassportElementErrorUnspecified` | `element_hash` | Unspecified error in an element. |

---

### Bot Methods

| Method | Returns | Description |
|---|---|---|
| `set_passport_data_errors(user_id, errors)` | `bool` | Inform user about errors in submitted Passport data. `errors` is `list[PassportElementError*]`. The user will not be able to resend data until all errors are cleared. |

## Common Patterns

### Decrypt and process passport data

```python
async def handle_passport(update: Update, context: ContextTypes.DefaultType):
    passport_data = update.message.passport_data

    for element in passport_data.decrypted_data:
        if element.type == "personal_details":
            details = element.decrypted_data
            print(f"{details.first_name} {details.last_name}, DOB: {details.date_of_birth}")

        elif element.type == "driver_license":
            doc = element.decrypted_data  # IdDocumentData
            print(f"License: {doc.document_no}, expires: {doc.expiry_date}")

            # Download front side
            front = await element.front_side.get_file()
            await front.download_to_drive("front_side.jpg")
```

### Report errors back to user

```python
from telegram import PassportElementErrorDataField, PassportElementErrorSelfie

async def validate_passport(update: Update, context: ContextTypes.DefaultType):
    errors = []
    for element in update.message.passport_data.decrypted_data:
        if element.type == "personal_details":
            details = element.decrypted_data
            if not details.first_name:
                errors.append(PassportElementErrorDataField(
                    type="personal_details",
                    field_name="first_name",
                    data_hash=element.hash,
                    message="First name is required.",
                ))

    if errors:
        await context.bot.set_passport_data_errors(
            user_id=update.effective_user.id,
            errors=errors,
        )
```

## Related

- [../bot.md](../bot.md) -- `Bot.set_passport_data_errors()`, private key configuration
- [../application.md](../application.md) -- `ApplicationBuilder.private_key()` for setting the decryption key
- [../handlers/message-handler.md](../handlers/message-handler.md) -- `MessageHandler` with `filters.PASSPORT_DATA`
- [../handlers/filters.md](../handlers/filters.md) -- `filters.PASSPORT_DATA`
- [../types/index.md](../types/index.md) -- base type system
- [Telegram API — Passport](../../api/bots/passport/index.md) -- Telegram Passport encryption and data handling in the API specification
