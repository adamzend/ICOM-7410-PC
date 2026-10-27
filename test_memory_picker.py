"""GUI checks with intercepted commands; does not connect to or retune hardware."""
import unittest
from unittest.mock import patch
from app import App

class MemoryPickerTests(unittest.TestCase):
    def test_selection_filter_and_connection_guards(self):
        with patch('app.input_devices',return_value=[]):
            app=App()
        sent=[]
        app.submit=lambda *args:sent.append(args)
        try:
            app.rows={1:dict(channel=1,name='LOCAL',rx=14500000,mode='USB',filter=2),
                      2:dict(channel=2,empty=True),
                      100:dict(channel=100,name='EDGE',rx=7000000,mode='LSB',filter=1)}
            app.open_memory_picker()
            app.update_idletasks()
            self.assertEqual(app.picker_table.get_children(),('1','100'))
            self.assertEqual(sent,[])
            app.picker_search.set('14,500')
            self.assertEqual(app.picker_table.get_children(),('1',))
            app.picker_table.selection_set('1')
            app.choose_memory_frequency()
            self.assertEqual(sent,[])
            app.connected=True
            app.busy=True
            app.choose_memory_frequency()
            self.assertEqual(sent,[])
            app.busy=False
            app.choose_memory_frequency()
            self.assertEqual(sent,[('recall',app.rows[1])])
            self.assertEqual(app.freq_entry.get(),'14.500000')
            app.picker_search.set('nothing')
            self.assertEqual(app.picker_table.get_children(),())
            app.choose_memory_frequency()
            self.assertEqual(len(sent),1)
            app.memory_picker.destroy()
            app.open_memory_picker()
            self.assertEqual(app.picker_table.get_children(),('1','100'))
        finally:
            app.busy=False
            app.close()

if __name__=='__main__':
    unittest.main(verbosity=2)
