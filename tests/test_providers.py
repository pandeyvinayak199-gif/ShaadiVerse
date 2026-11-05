import os, unittest
from unittest.mock import patch
import providers
class ProviderContracts(unittest.TestCase):
 def test_template_parameters_and_button_payloads(self):
  with patch.dict(os.environ,{'WHATSAPP_ACCESS_TOKEN':'fixture','WHATSAPP_PHONE_NUMBER_ID':'123','WHATSAPP_TEMPLATE_NAME':'invitation','WHATSAPP_RSVP_BUTTONS':'1'}),patch('providers.request',return_value={'messages':[{'id':'fixture'}]}) as request:
   providers.whatsapp_send('9888888800','Guest','Event','EVENT-CODE')
   data=request.call_args.args[1];self.assertEqual(data['to'],'919888888800');components=data['template']['components']
   self.assertEqual([p['text'] for p in components[0]['parameters']],['Guest','Event','EVENT-CODE'])
   self.assertEqual([c['parameters'][0]['payload'] for c in components[1:]],['RSVP_YES','RSVP_NO','RSVP_MAYBE'])
 def test_twilio_verification_uses_provider_approval(self):
  with patch.dict(os.environ,{'TWILIO_ACCOUNT_SID':'fixture','TWILIO_AUTH_TOKEN':'fixture','TWILIO_VERIFY_SERVICE_SID':'fixture'}),patch('providers.request',return_value={'status':'pending'}):self.assertFalse(providers.sms_check('9888888800','123456'))
