-- Schema additions for Mercury labs must be visible to PostgREST before REST read/write certification.
notify pgrst, 'reload schema';
