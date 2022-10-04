import * as scripts from './scripts';
import { __version__ } from './version';

frappe.provide('gwi');
gwi = { __version__, scripts };
