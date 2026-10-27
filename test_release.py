import unittest
from unittest.mock import patch,MagicMock
import urllib.error
import json
from radio import Radio
from app_info import check_release,repository_slug,version_tuple,open_info
from i18n import set_language,tr
from app import App

class ReleaseTests(unittest.TestCase):
    def tearDown(self):
        set_language('en')

    def test_profile_mode_data_tones_and_no_memory_write(self):
        radio=Radio.__new__(Radio)
        row=dict(rx=29500000,mode='FM',filter=2,extra=dict(rx_data=1,rx_tone=2,rx_ctcss=885,rx_tsql=1000))
        values={}
        radio.tune=MagicMock()
        radio.set_mode=MagicMock()
        radio.write_setting=MagicMock(side_effect=lambda key,value:values.update({key:value}))
        radio.read_setting=lambda key:values[key]
        radio.exchange=MagicMock()
        radio.state=lambda:dict(hz=row['rx'],mode=row['mode'],filter=row['filter'])
        radio.recall_profile(row)
        radio.tune.assert_called_once_with(29500000)
        radio.set_mode.assert_called_once_with('FM',2)
        self.assertEqual(values,dict(data=258,tone=885,tsql=1000,tone_on=0,tsql_on=1))
        radio.exchange.assert_not_called()
        values.clear()
        row.update(mode='USB')
        radio.recall_profile(row)
        self.assertEqual(values,{'data':258})
        row.update(mode='CW')
        radio.tune.reset_mock()
        with self.assertRaises(ValueError): radio.recall_profile(row)
        radio.tune.assert_not_called()

    def test_partial_recall_stops_and_is_not_replayed(self):
        radio=Radio.__new__(Radio)
        row=dict(rx=14200000,mode='USB',filter=2,extra=dict(rx_data=0,rx_tone=0,rx_ctcss=885,rx_tsql=885))
        radio.tune=MagicMock()
        radio.set_mode=MagicMock(side_effect=TimeoutError('test timeout'))
        radio.write_setting=MagicMock()
        with self.assertRaisesRegex(RuntimeError,'incomplete'):
            radio.recall_profile(row)
        radio.tune.assert_called_once()
        radio.set_mode.assert_called_once()
        radio.write_setting.assert_not_called()

    def test_update_check_is_read_only_and_handles_no_release(self):
        self.assertEqual(repository_slug('https://github.com/adamzend/ICOM-7410-PC'),'adamzend/ICOM-7410-PC')
        for bad in ['http://github.com/a/b','https://evil.test/a/b','https://github.com/a/b?token=x']:
            with self.assertRaises(ValueError): repository_slug(bad)
        with patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('url',404,'missing',{},None)):
            message,link=check_release('https://github.com/adamzend/ICOM-7410-PC')
            self.assertIn('not available',message)
            self.assertIsNone(link)
        response=MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'tag_name':'v0.4.0','html_url':'https://evil.test'}).encode()
        with patch('urllib.request.urlopen',return_value=response) as request:
            message,link=check_release('https://github.com/adamzend/ICOM-7410-PC')
            self.assertEqual(request.call_args.args[0].get_method(),'GET')
            self.assertEqual(link,'https://github.com/adamzend/ICOM-7410-PC/releases/latest')
        self.assertEqual(version_tuple('v1.10.0'),(1,10,0))
        self.assertIsNone(version_tuple('v1.0.0-beta'))

    def test_language_switch_preserves_radio_audio_and_editor(self):
        with patch('app.input_devices',return_value=[]),patch('urllib.request.urlopen') as network:
            app=App()
            try:
                self.assertEqual(app.title(),'ICOM-7410-PC')
                self.assertEqual(app.connect_btn.cget('text'),'Connect')
                worker=app.worker
                app.freq_entry.set('14.200000')
                app.edit['name'].set('TEST')
                app.setting_values={'tone':885}
                app.fill_settings_tree()
                app.settings_tree.selection_set('tone')
                app.render_setting_editor()
                app.change_language('pl')
                self.assertEqual(app.connect_btn.cget('text'),'Połącz')
                self.assertIs(app.worker,worker)
                self.assertEqual(app.freq_entry.get(),'14.200000')
                self.assertEqual(app.edit['name'].get(),'TEST')
                app.change_language('en')
                self.assertEqual(app.connect_btn.cget('text'),'Connect')
                open_info(app)
                app.update_idletasks()
                self.assertTrue(app.info_window.winfo_exists())
                network.assert_not_called()
            finally:
                app.close()

    def test_missing_usb_does_not_select_pc_microphone(self):
        with patch('app.input_devices',return_value=[(1,'PC microphone [MME]')]),patch('app.AudioInput') as audio:
            app=App()
            try:
                self.assertEqual(app.device.get(),'')
                app.toggle_audio()
                audio.assert_not_called()
                self.assertIsNone(app.audio)
            finally:
                app.close()

if __name__=='__main__':
    unittest.main(verbosity=2)
