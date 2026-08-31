---
title: "Contact ChinaBound Travel"
date: "2026-07-08T10:00:00+08:00"
description: "Get in touch with ChinaBound Travel for questions about China travel, collaboration opportunities, or advertising inquiries. Use our contact form or email us directly."
slug: "contact"
ShowToc: "false"
---

## Get in Touch

Have a question about traveling in China that isn't covered in our guides? Want to collaborate on content, or discuss advertising opportunities? We'd love to hear from you.

Fill out the form below and we'll get back to you as soon as possible.

<div class="contact-form-container">
  <form id="contact-form" action="https://api.web3forms.com/submit" method="POST">
    <div class="form-group">
      <label for="name">Your Name <span class="required">*</span></label>
      <input type="text" id="name" name="name" required placeholder="John Smith" autocomplete="name">
    </div>

    <div class="form-group">
      <label for="email">Email Address <span class="required">*</span></label>
      <input type="email" id="email" name="email" required placeholder="john@example.com" autocomplete="email">
    </div>

    <div class="form-group">
      <label for="subject">Subject <span class="required">*</span></label>
      <select id="subject" name="subject" required>
        <option value="">-- Select a topic --</option>
        <option value="China Travel Question">China Travel Question</option>
        <option value="Visa / Entry Requirements">Visa / Entry Requirements</option>
        <option value="Payment (Alipay/WeChat Pay)">Payment (Alipay/WeChat Pay)</option>
        <option value="Collaboration / Partnership">Collaboration / Partnership</option>
        <option value="Advertising Inquiry">Advertising Inquiry</option>
        <option value="Feedback / Correction">Feedback / Correction</option>
        <option value="Other">Other</option>
      </select>
    </div>

    <div class="form-group">
      <label for="message">Your Message <span class="required">*</span></label>
      <textarea id="message" name="message" rows="6" required placeholder="Tell us how we can help..."></textarea>
    </div>

    <div class="form-group form-checkbox">
      <input type="checkbox" id="consent" name="consent" required>
      <label for="consent">I agree to have my name and email stored for the purpose of responding to my inquiry.</label>
    </div>

    <!-- Web3Forms Configuration -->
    <input type="hidden" name="access_key" value="783e3635-8748-4a28-bb96-520a68ae9d02">
    <input type="hidden" name="from_name" value="ChinaBound Travel Contact Form">
    <input type="hidden" name="replyto" value="">
    <input type="checkbox" name="botcheck" style="display:none">

    <button type="submit" class="btn btn-primary">Send Message</button>
  </form>

  <div id="form-success" style="display:none;">
    <div class="form-success-message">
      <h3>✓ Message Sent!</h3>
      <p>Thank you for reaching out. We've received your message and will get back to you within 24-48 hours.</p>
      <p><a href="/" class="btn btn-secondary">← Back to Home</a></p>
    </div>
  </div>

  <div id="form-error" style="display:none;">
    <div class="form-error-message">
      <h3>✗ Something went wrong</h3>
      <p>We couldn't send your message. Please try again, or email us directly at <a href="mailto:joran@chinaboundtravel.com">joran@chinaboundtravel.com</a>.</p>
    </div>
  </div>
</div>

### Or Email Us Directly

**Email:** [joran@chinaboundtravel.com](mailto:joran@chinaboundtravel.com)

### What We Can Help With

- China travel itinerary planning advice
- Visa and entry requirement questions
- Payment setup (Alipay/WeChat Pay) troubleshooting
- General China travel safety concerns
- Business inquiries and partnerships
- Content corrections and updates

### Response Time

We do our best to respond within **24-48 hours**. For urgent travel questions, leaving a comment on the relevant article is often the fastest way to get a response, as we check comments regularly.

### Collaboration

If you're a fellow travel blogger, tourism board, or hospitality brand interested in working together, please reach out with specifics about your proposal. We're always open to authentic partnerships that benefit our readers.

---

*We respect your privacy. Your contact information is only used to respond to your inquiry and is never shared with third parties. See our [Privacy Policy](/privacy-policy/) for details.*

<style>
.contact-form-container {
  max-width: 640px;
  margin: 2rem 0;
}
.form-group {
  margin-bottom: 1.25rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.4rem;
  font-weight: 600;
  font-size: 0.95rem;
}
.form-group .required {
  color: #e74c3c;
}
.form-group input[type="text"],
.form-group input[type="email"],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.7rem 0.9rem;
  border: 1px solid var(--border, #ddd);
  border-radius: 6px;
  font-size: 1rem;
  background: var(--entry, #fff);
  color: var(--content, #333);
  box-sizing: border-box;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}
.form-group textarea {
  resize: vertical;
  min-height: 120px;
}
.form-checkbox {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
}
.form-checkbox input[type="checkbox"] {
  margin-top: 0.25rem;
  width: auto;
}
.form-checkbox label {
  font-weight: 400;
  font-size: 0.85rem;
  margin-bottom: 0;
}
.btn {
  display: inline-block;
  padding: 0.75rem 1.75rem;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  border: none;
  transition: background 0.2s, transform 0.1s;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
}
.btn-primary:hover {
  background: #1d4ed8;
}
.btn-primary:active {
  transform: translateY(1px);
}
.btn-secondary {
  background: var(--tertiary, #f0f0f0);
  color: var(--content, #333);
}
.form-success-message,
.form-error-message {
  padding: 1.5rem;
  border-radius: 8px;
  margin: 1rem 0;
}
.form-success-message {
  background: #ecfdf5;
  border: 1px solid #10b981;
}
.form-success-message h3 {
  color: #059669;
  margin-top: 0;
}
.form-error-message {
  background: #fef2f2;
  border: 1px solid #ef4444;
}
.form-error-message h3 {
  color: #dc2626;
  margin-top: 0;
}
</style>

<script>
(function() {
  const form = document.getElementById('contact-form');
  const successDiv = document.getElementById('form-success');
  const errorDiv = document.getElementById('form-error');

  if (!form) return;

  // Auto-set replyto from email field
  const emailInput = document.getElementById('email');
  const replytoInput = form.querySelector('input[name="replyto"]');
  if (emailInput && replytoInput) {
    emailInput.addEventListener('input', function() {
      replytoInput.value = this.value;
    });
  }

  form.addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Sending...';
    submitBtn.disabled = true;

    try {
      const response = await fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json'
        }
      });

      const result = await response.json();

      if (response.ok && result.success) {
        form.style.display = 'none';
        successDiv.style.display = 'block';
        errorDiv.style.display = 'none';
      } else {
        throw new Error(result.message || 'Form submission failed');
      }
    } catch (err) {
      console.error('Form error:', err);
      errorDiv.style.display = 'block';
      submitBtn.textContent = originalText;
      submitBtn.disabled = false;
    }
  });
})();
</script>
