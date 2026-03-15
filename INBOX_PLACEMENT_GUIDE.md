# Email Inbox Placement Guide

## Why Emails Go to "All Mail" Instead of Primary Inbox

Gmail uses machine learning to classify emails into:
- **Primary** - Personal emails, transactional messages
- **Promotions** - Marketing emails, newsletters
- **Social** - Social network notifications
- **All Mail** - Everything (includes all categories)

## ✅ What We Fixed in Code

### 1. **Better Email Headers** (just added)
```python
msg['Reply-To'] = sender_email
msg['X-Mailer'] = 'The 80% Bill Email System'
msg['X-Priority'] = '3'  # Normal priority
msg['List-Unsubscribe'] = '<mailto:info@the80percentbill.com?subject=unsubscribe>'
msg['Message-ID'] = '<unique-id@the80percentbill.com>'
```

**Why it helps:**
- Reply-To makes emails more legitimate
- List-Unsubscribe is CAN-SPAM compliant
- Message-ID helps with threading and legitimacy
- Proper headers signal this is a real email, not spam

### 2. **Plain Text + HTML**
Always send both:
- Plain text version first (better spam score)
- HTML version second (for design)

### 3. **Proper From Name**
Using: `The 80% Bill <info@the80percentbill.com>`
Not just: `info@the80percentbill.com`

---

## 🔧 Additional Setup Required (Not in Code)

### 1. **SPF Record** ✅ (Check if done)
Add to DNS for `the80percentbill.com`:
```
TXT record:
v=spf1 include:spf.brevo.com ~all
```

**Check:** https://mxtoolbox.com/spf.aspx?domain=the80percentbill.com

### 2. **DKIM Signing** ✅ (Should be automatic with Brevo)
Brevo adds DKIM signatures automatically when you verify your domain.

**Verify in Brevo dashboard:**
- Settings → Senders & IP → Domain Authentication
- Make sure `the80percentbill.com` shows as "Authenticated"

### 3. **DMARC Policy** ⚠️ (Recommended)
Add to DNS:
```
TXT record for _dmarc.the80percentbill.com:
v=DMARC1; p=none; rua=mailto:dmarc@the80percentbill.com; pct=100
```

**Why:** Tells Gmail you're serious about email security

### 4. **Warm Up Your Domain** 🔥
**Problem:** New sender = untrusted = promotions/spam

**Solution:**
1. Start with 10-20 emails/day to engaged users
2. Gradually increase over 2-3 weeks
3. Reach 100-500/day, then scale

**Schedule:**
- Week 1: 10-20 emails/day
- Week 2: 50-100 emails/day  
- Week 3: 200-300 emails/day
- Week 4+: Full volume

---

## 📝 Content Best Practices

### ✅ DO:
1. **Personal tone** - Write like a human, not a marketer
2. **Clear subject lines** - Avoid "RE:", "FWD:", excessive caps
3. **Include recipient name** - "Hi {{first_name}},"
4. **Real reply address** - info@the80percentbill.com works
5. **Unsubscribe link** - Always visible in footer
6. **Balance text/images** - 60% text, 40% images
7. **Proper HTML** - Use tables for layout (email clients are old)
8. **Mobile-friendly** - Responsive design

### ❌ AVOID:
1. **Spam trigger words:**
   - "Free!", "Act now!", "Limited time!", "Click here!"
   - ALL CAPS SUBJECT LINES
   - Multiple exclamation points!!!
   
2. **Too many links** - Keep under 5 links per email

3. **Large images** - Keep under 100KB each

4. **Misleading subject lines** - Subject must match content

5. **No-reply addresses** - Use real addresses

6. **Purchased email lists** - Only email people who opted in

7. **URL shorteners** - Use full URLs (bit.ly triggers spam filters)

---

## 🎯 Template-Specific Tips

### For Political/Advocacy Emails:
1. **Use personal stories** - "I signed because..."
2. **Specific asks** - "Call your rep at {{phone}}"
3. **Urgency without hype** - "Vote is Tuesday" not "ACT NOW!!!"
4. **Local context** - Mention {{district}} and {{representative_name}}

### Example Subject Lines:
✅ Good:
- "Your representative needs to hear from you"
- "{{first_name}}, here's what's happening in {{district}}"
- "The vote is next week — here's how to help"

❌ Bad:
- "URGENT: ACT NOW!!!"
- "You won't believe this..."
- "RE: Your support needed"

---

## 📊 Testing & Monitoring

### 1. **Send Test Emails**
Before campaigns, send to:
- Gmail
- Yahoo
- Outlook/Hotmail
- ProtonMail

Check which folder they land in.

### 2. **Mail-Tester Score**
Send test email to: https://www.mail-tester.com/
- Aim for 8/10 or higher
- Shows SPF/DKIM/DMARC status
- Highlights spam trigger words

### 3. **Gmail Postmaster Tools**
Sign up: https://postmaster.google.com/
- See your domain reputation
- Track spam rate
- Monitor delivery errors

### 4. **Monitor Metrics**
Track in your EmailLog:
- **Open rate** - Should be >20%
- **Click rate** - Should be >2%
- **Bounce rate** - Should be <2%
- **Spam complaints** - Should be <0.1%

---

## 🚀 Quick Wins (Do These First)

1. ✅ **Verify domain in Brevo** - Check DKIM is active
2. ✅ **Add SPF record** - Include Brevo's servers
3. ✅ **Test current emails** - Use mail-tester.com
4. ✅ **Review templates** - Remove spam trigger words
5. ✅ **Start small** - Send 10-20 emails/day first
6. ⚠️ **Ask recipients to star/reply** - Signals engagement

---

## 💡 The "Move to Primary" Trick

**Ask early recipients:**
> "To make sure you don't miss future updates, please:
> 1. Move this email to your Primary inbox
> 2. Mark it as 'Not spam' if it's in spam
> 3. Add info@the80percentbill.com to your contacts"

**Why it works:**
- Gmail learns from individual user actions
- If enough people move emails to Primary, Gmail adapts
- Engagement signals (opens, clicks, replies) boost placement

---

## 🔍 Debugging Steps

If emails still go to Promotions:

1. **Check DNS records:**
   ```bash
   dig TXT the80percentbill.com
   dig TXT _dmarc.the80percentbill.com
   ```

2. **Test email:**
   - Send to mail-tester.com
   - Check score (must be 8+/10)

3. **Review content:**
   - Remove marketing language
   - Add more personal tone
   - Include plain text version

4. **Check Brevo reputation:**
   - Brevo dashboard → Statistics
   - Look for high bounce/complaint rates

5. **Ask test users:**
   - Did they mark as "Not spam"?
   - Did they move to Primary?
   - Did they click/reply?

---

## 📚 Resources

- **SPF/DKIM checker:** https://mxtoolbox.com/
- **Email tester:** https://www.mail-tester.com/
- **Gmail Postmaster:** https://postmaster.google.com/
- **Brevo docs:** https://help.brevo.com/hc/en-us/articles/360000991960

---

## Summary Checklist

- [x] Email headers improved (Reply-To, Message-ID, List-Unsubscribe)
- [x] Plain text + HTML versions
- [ ] **Verify SPF record in DNS**
- [ ] **Verify DKIM in Brevo dashboard**
- [ ] **Add DMARC record (optional but recommended)**
- [ ] **Test score on mail-tester.com (aim for 8+/10)**
- [ ] **Start with 10-20 emails/day, warm up over 2-3 weeks**
- [ ] **Remove spam trigger words from templates**
- [ ] **Ask early recipients to move emails to Primary**
- [ ] **Monitor Gmail Postmaster Tools**

**The most important factors:**
1. ✅ Proper authentication (SPF/DKIM/DMARC)
2. ✅ Gradual warm-up (don't blast 1000 emails day 1)
3. ✅ Engagement (opens, clicks, replies)
4. ✅ Content quality (personal, not promotional)
