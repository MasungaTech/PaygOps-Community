from pony import orm

def chunker(seq, size):
        return (seq[pos:pos + size] for pos in range(0, len(seq), size))

def isolated_chunk_executer(ids, base_object, function, action_name='', chunk_size=100):
    count = len(ids)
    initial_count = count
    if count > 0:
        print(f'{count} to process for {action_name} in batches of {chunk_size}')
        for ids_chunk in chunker(ids, chunk_size):
            try:
                with orm.db_session:
                    objs = orm.select(p for p in base_object if p.id in ids_chunk)
                    for obj in objs:
                        function(obj)
            except Exception as e:
                print(f'Error on processing objects: {e}')
                if chunk_size != 1:
                    isolated_chunk_executer(ids_chunk, base_object, function, action_name, int(chunk_size/10))
            count = max(count-chunk_size, 0)
            print(f'{count}/{initial_count} left to process for {action_name}')