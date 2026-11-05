"""Provider adapters: never return credentials or silently replace live calls with mocks."""
import os, json, base64, urllib.request, urllib.parse, urllib.error

class ProviderError(Exception): pass

def request(url, data=None, bearer=None, basic=None, form=False):
    headers={'Accept':'application/json'}
    if bearer: headers['Authorization']='Bearer '+bearer
    if basic: headers['Authorization']='Basic '+base64.b64encode((':'.join(basic)).encode()).decode()
    payload=None
    if data is not None:
        headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
        payload=urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,data=payload,headers=headers),timeout=20) as response:
            return json.load(response)
    except (urllib.error.URLError,ValueError):
        raise ProviderError('Provider request failed. Check credentials, account approval and provider logs.') from None

def configured(*names): return all(os.environ.get(n) for n in names)
def sms_ready():return configured('TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_VERIFY_SERVICE_SID')
def whatsapp_ready():return configured('WHATSAPP_ACCESS_TOKEN','WHATSAPP_PHONE_NUMBER_ID','WHATSAPP_TEMPLATE_NAME')
def payments_ready():return configured('RAZORPAY_KEY_ID','RAZORPAY_KEY_SECRET','RAZORPAY_WEBHOOK_SECRET')
def sms_send(phone):
    if not sms_ready(): raise ProviderError('Phone verification is not configured. The organiser must connect Twilio Verify.')
    return request('https://verify.twilio.com/v2/Services/'+os.environ['TWILIO_VERIFY_SERVICE_SID']+'/Verifications',{'To':'+91'+phone,'Channel':'sms'},basic=(os.environ['TWILIO_ACCOUNT_SID'],os.environ['TWILIO_AUTH_TOKEN']),form=True)
def sms_check(phone,code):
    if not sms_ready():raise ProviderError('Phone verification is not configured.')
    result=request('https://verify.twilio.com/v2/Services/'+os.environ['TWILIO_VERIFY_SERVICE_SID']+'/VerificationCheck',{'To':'+91'+phone,'Code':code},basic=(os.environ['TWILIO_ACCOUNT_SID'],os.environ['TWILIO_AUTH_TOKEN']),form=True)
    return result.get('status')=='approved'
def whatsapp_send(phone,guest,event,code):
    if not whatsapp_ready():raise ProviderError('WhatsApp Business is not configured.')
    components=[{'type':'body','parameters':[{'type':'text','text':x} for x in (guest,event,code)]}]
    if os.environ.get('WHATSAPP_RSVP_BUTTONS','0')=='1':
        components.extend({'type':'button','sub_type':'quick_reply','index':str(i),'parameters':[{'type':'payload','payload':payload}]} for i,payload in enumerate(['RSVP_YES','RSVP_NO','RSVP_MAYBE']))
    return request('https://graph.facebook.com/'+os.environ.get('WHATSAPP_API_VERSION','v23.0')+'/'+os.environ['WHATSAPP_PHONE_NUMBER_ID']+'/messages',{
        'messaging_product':'whatsapp','to':'91'+phone,'type':'template','template':{'name':os.environ['WHATSAPP_TEMPLATE_NAME'],'language':{'code':os.environ.get('WHATSAPP_TEMPLATE_LANGUAGE','en')},'components':components}},bearer=os.environ['WHATSAPP_ACCESS_TOKEN'])
def payment_request(path,data=None):
    if not payments_ready():raise ProviderError('Razorpay is not configured.')
    return request('https://api.razorpay.com/v1/'+path,data,basic=(os.environ['RAZORPAY_KEY_ID'],os.environ['RAZORPAY_KEY_SECRET']))
